"""ProviderDefinition contract (Toonflow crown jewel, ported to Python).

A provider declares {id, label, version, rules[], models[]} plus optional
capabilities: generate_image / generate_video / generate_audio /
get_price / get_balance / process_media. Generate functions return FINAL
media assets, never task IDs. Free providers use rules: [] (no apiKey) and
hardcode their model list.

Third-party provider modules are loaded via importlib and treated as
trusted code (per Toonflow's model).
"""

from __future__ import annotations

import mimetypes
import os
import threading
import uuid

from .. import definition as d

MAX_REFERENCE_BYTES = 25 * 1024 * 1024  # 25 MiB per reference file
GENERATED_DIRNAME = "generated"


def sniff_image_kind(data):
    """Minimal image magic-byte sniff (replaces deprecated imghdr)."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:2] == b"BM":
        return "bmp"
    return None

_MIME_BY_EXT = {
    ".mp4": "video/mp4", ".mov": "video/quicktime",
    ".webm": "video/webm", ".mkv": "video/x-matroska",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif",
    ".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
    ".flac": "audio/flac", ".ogg": "audio/ogg",
}


class ProviderContext:
    """Host-injected context: config + cancel event + file lock helper."""

    def __init__(self, config=None, cancelled=None):
        self.config = dict(config or {})
        self.cancelled = cancelled  # threading.Event or None

    def check_cancelled(self):
        if self.cancelled is not None and self.cancelled.is_set():
            raise d.CancelledError("cancelled by request")


class ProviderDefinition:
    """Base class / contract for providers."""

    id = ""
    label = ""
    version = "1"
    rules = []    # e.g. [{"field": "apiKey", "label": "...", "secret": True}]
    models = []   # e.g. [{"id": "...", "label": "...", "type": "video"}]

    # -- capabilities: keep unimplemented ones ABSENT (not None-returning) --
    # generate_image(ctx, request) -> list[MediaAsset]
    # generate_video(ctx, request) -> list[MediaAsset]
    # generate_audio(ctx, request) -> list[MediaAsset]
    # get_price(ctx, request) -> {"price": str, "tips": str} | None
    # get_balance(ctx) -> {"balance": float, "unit": str}
    # process_media(ctx, request) -> request (may be async-free; sync ok)

    def has(self, capability):
        return callable(getattr(self, capability, None))

    def model_ids(self):
        return [m["id"] for m in self.models if "id" in m]

    def validate_config(self):
        missing = [r["field"] for r in self.rules
                   if r.get("required", True) and not self._cfg().get(r["field"])]
        if missing:
            raise d.PipelineBlockedError(
                f"provider {self.id!r}: missing config: {', '.join(missing)}")

    def _cfg(self):
        return getattr(self, "_config", {})


def bind(provider, config=None, cancelled=None):
    """Attach a ProviderContext to a provider instance."""
    provider._config = dict(config or {})
    provider._ctx = ProviderContext(provider._config, cancelled)
    return provider


# --- reference-file reading (mime-sniffed, size-capped) -----------------------
def sniff_mime(path, data):
    kind = sniff_image_kind(data[:32])
    if kind:
        return {"jpeg": "image/jpeg", "png": "image/png",
                "gif": "image/gif", "webp": "image/webp",
                "bmp": "image/bmp"}[kind]
    # audio magic
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if data[:3] == b"ID3" or data[:2] == b"\xff\xfb":
        return "audio/mpeg"
    if data[:4] in (b"\x1aE\xdf\xa3",):
        return "video/webm"
    if len(data) > 8 and data[4:8] == b"ftyp":
        return "video/mp4"
    ext = os.path.splitext(path)[1].lower()
    return _MIME_BY_EXT.get(ext, mimetypes.guess_type(path)[0]
                            or "application/octet-stream")


def read_reference(path, max_bytes=MAX_REFERENCE_BYTES):
    """Read a reference file: size-capped, mime-sniffed. Returns
    {"type": "binary", "data": bytes, "mimeType": str, "name": str}."""
    size = os.path.getsize(path)
    if size > max_bytes:
        raise d.PipelineError(
            f"reference file too large: {path!r} ({size} bytes > "
            f"{max_bytes} cap)")
    with open(path, "rb") as fh:
        data = fh.read()
    return {"type": "binary", "data": data,
            "mimeType": sniff_mime(path, data),
            "name": os.path.basename(path)}


# --- generateMedia host flow ---------------------------------------------------
_GENERATED_LOCKS = {}
_GENERATED_LOCKS_GUARD = threading.Lock()


def _lock_for(directory):
    with _GENERATED_LOCKS_GUARD:
        lock = _GENERATED_LOCKS.get(directory)
        if lock is None:
            lock = _GENERATED_LOCKS[directory] = threading.Lock()
        return lock


def _normalize_asset(asset):
    """Provider assets may be {url|base64|data bytes}. Return a file asset."""
    if not isinstance(asset, dict):
        raise d.ProviderError(f"provider returned non-dict asset: {type(asset)}")
    media_type = asset.get("mediaType")
    if media_type not in ("image", "video", "audio"):
        raise d.ProviderError(f"bad asset mediaType: {media_type!r}")
    mime = asset.get("mimeType") or ""
    data = None
    if isinstance(asset.get("data"), (bytes, bytearray)):
        data = bytes(asset["data"])
    elif isinstance(asset.get("base64"), str):
        import base64
        data = base64.b64decode(asset["base64"])
    elif isinstance(asset.get("url"), str) and os.path.exists(asset["url"]):
        with open(asset["url"], "rb") as fh:
            data = fh.read()
        mime = mime or sniff_mime(asset["url"], data)
    if data is None:
        raise d.ProviderError(
            "provider asset carried no data (need data bytes, base64, or "
            "an existing file url)")
    if not mime:
        mime = {"image": "image/png", "video": "video/mp4",
                "audio": "audio/wav"}[media_type]
    return media_type, mime, data


def _ext_for(mime, media_type):
    ext = mimetypes.guess_extension(mime) or ""
    if ext in (".jpe",):
        ext = ".jpg"
    return ext or {"image": ".png", "video": ".mp4",
                   "audio": ".wav"}[media_type]


def generate_media(provider, kind, request, out_dir, config=None,
                   cancelled=None, max_reference_bytes=MAX_REFERENCE_BYTES):
    """Host flow: validate -> resolve provider+model -> read references
    (mime-sniffed, size-capped) -> call provider -> normalize assets ->
    write assets/generated/<type>_<uuid>.<ext> under a file lock.

    Returns list of {"url" (path), "mimeType"}. On error, deletes only the
    files this call created. Raises the provider error (redacted)."""
    cap = {"image": "generate_image", "video": "generate_video",
           "audio": "generate_audio"}[kind]
    if not provider.has(cap):
        raise d.PipelineBlockedError(
            f"provider {provider.id!r} has no {cap} capability")
    prompt = (request or {}).get("prompt") or (request or {}).get("text") or ""
    if not str(prompt).strip():
        raise d.PipelineError("generate_media: empty prompt/text")
    model = (request or {}).get("model") or ""
    if model and model not in provider.model_ids():
        raise d.PipelineError(
            f"provider {provider.id!r}: unknown model {model!r} "
            f"(have: {', '.join(provider.model_ids()) or 'none'})")

    refs = []
    for ref_path in (request or {}).get("reference_paths") or []:
        refs.append(read_reference(ref_path, max_reference_bytes))

    ctx = ProviderContext(config, cancelled)
    fn = getattr(provider, cap)
    call_request = dict(request or {})
    call_request["references"] = refs
    created = []
    try:
        try:
            raw_assets = fn(ctx, call_request)
        except (d.PipelineBlockedError, d.CancelledError):
            raise
        except Exception as exc:  # provider bugs -> ProviderError, redacted
            raise d.ProviderError(
                f"provider {provider.id!r} {cap} failed: "
                f"{d.redact_secrets(exc)}") from exc
        if not isinstance(raw_assets, list) or not raw_assets:
            raise d.ProviderError(
                f"provider {provider.id!r} {cap} returned no assets "
                "(generate functions must return FINAL media, never task IDs)")
        os.makedirs(out_dir, exist_ok=True)
        out = []
        with _lock_for(out_dir):
            for asset in raw_assets:
                media_type, mime, data = _normalize_asset(asset)
                name = (f"{media_type}_{uuid.uuid4().hex}"
                        f"{_ext_for(mime, media_type)}")
                path = os.path.join(out_dir, name)
                with open(path, "wb") as fh:
                    fh.write(data)
                created.append(path)
                out.append({"url": path, "mimeType": mime,
                            "mediaType": media_type})
        return out
    except BaseException:
        for path in created:  # delete only files this call created
            try:
                os.unlink(path)
            except OSError:
                pass
        raise
