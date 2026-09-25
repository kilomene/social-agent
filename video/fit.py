"""Smart aspect-ratio fitter: the agent always knows the right size.

Core rule: NEVER destroy content by default. A mismatch is solved by PADDING
(blurred-background fill), which preserves 100% of the source frame. Cropping
is destructive and runs ONLY with an explicit --crop plus a focus point that
tells the agent what to keep; without a focus point, crop is refused with an
explanation (see policy/guardrails.md: "never crop blindly").

Placements look like "tiktok", "tiktok:feed", "youtube:shorts". A bare platform
name uses that platform's default placement (first in specs.yaml).
"""

import json
import os
import subprocess
import tempfile

from . import ffmpeg as ff
from policy import yaml_lite

SPECS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "specs.yaml")

ASPECT_TOLERANCE = 0.02  # relative tolerance when comparing aspect ratios

# face detection is an optional enhancement (see video/SPECS.md); the fitter
# falls back to center focus with a warning when OpenCV is not installed.
try:
    import cv2  # noqa: F401
    _HAS_CV2 = True
except Exception:
    cv2 = None
    _HAS_CV2 = False


def has_face_detection():
    return _HAS_CV2


def load_specs():
    with open(SPECS_PATH, encoding="utf-8") as fh:
        return yaml_lite.loads(fh.read())


def default_placement(platform, specs=None):
    specs = specs or load_specs()
    if platform not in specs:
        raise ValueError(f"unknown platform {platform!r} "
                         f"(pick: {', '.join(sorted(specs))})")
    return next(iter(specs[platform]))


def lookup(target, specs=None):
    """Resolve 'tiktok' / 'tiktok:feed' -> (platform, placement, spec dict)."""
    specs = specs or load_specs()
    if ":" in target:
        platform, placement = target.split(":", 1)
    else:
        platform, placement = target, default_placement(target, specs)
    if platform not in specs:
        raise ValueError(f"unknown platform {platform!r} "
                         f"(pick: {', '.join(sorted(specs))})")
    if placement not in specs[platform]:
        raise ValueError(f"unknown placement {placement!r} for {platform} "
                         f"(pick: {', '.join(sorted(specs[platform]))})")
    return platform, placement, specs[platform][placement]


def aspect_ratio(w, h):
    return w / h if h else 0


def target_ratio(spec):
    tw, th = spec["width"], spec["height"]
    return tw / th


def aspect_matches(spec, w, h):
    """True when the source aspect matches the target (or an accepted alternate)."""
    src = aspect_ratio(w, h)
    tgt = target_ratio(spec)
    if abs(src - tgt) / tgt <= ASPECT_TOLERANCE:
        return "primary"
    for alt in spec.get("accepted_aspects", []) or []:
        aw, ah = (int(x) for x in str(alt).split(":"))
        if abs(src - (aw / ah)) / (aw / ah) <= ASPECT_TOLERANCE:
            return "alternate"
    return None


def _even(n):
    n = int(round(n))
    return n if n % 2 == 0 else n + 1


FOCUS_POINTS = {
    "center": (0.5, 0.5),
    "top": (0.5, 0.0),
    "bottom": (0.5, 1.0),
    "left": (0.0, 0.5),
    "right": (1.0, 0.5),
}


def detect_face_focus(input_path, at=3.0):
    """Return (fx, fy) of the largest detected face, or None.

    Requires OpenCV. Extracts one frame, runs a Haar cascade, and returns the
    centroid of the largest face as fractions of the frame. Returns (None,
    warning) when unavailable so callers can fall back gracefully.
    """
    if not _HAS_CV2:
        return None, "opencv not installed — --focus face falls back to center (see video/SPECS.md)"
    if not ff.which_ffmpeg():
        return None, "ffmpeg not found — cannot extract a frame for face detection"
    cascade_path = os.path.join(cv2.data.haarcascades,
                                "haarcascade_frontalface_default.xml")
    if not os.path.exists(cascade_path):
        return None, "face cascade model missing — falling back to center"
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp.close()
    try:
        argv = [ff.FFMPEG, "-y", "-v", "error", "-ss", str(at), "-i",
                input_path, "-frames:v", "1", tmp.name]
        proc = subprocess.run(argv, capture_output=True, text=True)
        if proc.returncode != 0:
            return None, "frame extraction failed — falling back to center"
        img = cv2.imread(tmp.name)
        if img is None:
            return None, "could not read frame — falling back to center"
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = cv2.CascadeClassifier(cascade_path).detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))
        if len(faces) == 0:
            return None, "no face detected in frame — falling back to center"
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        ih, iw = img.shape[:2]
        return (x + w / 2) / iw, (y + h / 2) / ih, None
    finally:
        try:
            os.remove(tmp.name)
        except OSError:
            pass


def resolve_focus(focus, focus_x=None, focus_y=None, input_path=None):
    """Return ((fx, fy), warnings). Raises UsageError-style ValueError when a
    crop was requested without any focus information."""
    warnings = []
    if focus_x is not None or focus_y is not None:
        if focus_x is None or focus_y is None:
            raise ValueError("both --focus-x and --focus-y are required together")
        return (float(focus_x), float(focus_y)), warnings
    if focus is None:
        raise ValueError(
            "refusing crop without a focus point: cropping is destructive and "
            "can cut the important part of the frame. Re-run with "
            "--focus center|top|bottom|left|right|face or "
            "--focus-x/--focus-y. Prefer padding (the default) to keep 100% "
            "of the frame.")
    focus = focus.lower()
    if focus == "face":
        got = detect_face_focus(input_path)
        if got[0] is None:
            warnings.append(got[1])
            return (0.5, 0.5), warnings
        return (got[0], got[1]), warnings
    if focus not in FOCUS_POINTS:
        raise ValueError(f"unknown focus {focus!r} "
                         f"(pick: {', '.join(sorted(FOCUS_POINTS))} or face)")
    return FOCUS_POINTS[focus], warnings


def crop_box(sw, sh, tw, th, fx, fy):
    """Cover-scale math for a crop-to-fill: returns (SW2, SH2, ox, oy) —
    the scaled frame size and the top-left of the crop box, all even ints."""
    f = max(tw / sw, th / sh)
    SW2, SH2 = _even(sw * f), _even(sh * f)
    ox = _even((SW2 - tw) * min(max(fx, 0.0), 1.0))
    oy = _even((SH2 - th) * min(max(fy, 0.0), 1.0))
    ox = min(max(ox, 0), SW2 - tw)
    oy = min(max(oy, 0), SH2 - th)
    return SW2, SH2, ox, oy


def crop_report(sw, sh, tw, th, fx, fy):
    """Human-readable description of what a crop WILL cut."""
    SW2, SH2, ox, oy = crop_box(sw, sh, tw, th, fx, fy)
    cut_w, cut_h = SW2 - tw, SH2 - th
    lost_pct = (1 - (tw * th) / (SW2 * SH2)) * 100
    edges = []
    if cut_w > 0:
        if ox > 0:
            edges.append(f"left ({ox}px)")
        if ox < SW2 - tw:
            edges.append(f"right ({SW2 - tw - ox}px)")
    if cut_h > 0:
        if oy > 0:
            edges.append(f"top ({oy}px)")
        if oy < SH2 - th:
            edges.append(f"bottom ({SH2 - th - oy}px)")
    return {
        "lost_pct": round(lost_pct, 1),
        "edges": edges,
        "box": {"scaled": [SW2, SH2], "offset": [ox, oy], "size": [tw, th]},
        "summary": (f"crop cuts {lost_pct:.1f}% of the frame — "
                    + (", ".join(edges) if edges else "nothing") + " removed"),
    }


def plan(info, target, crop=False, focus=None, focus_x=None, focus_y=None,
         specs=None):
    """Decide the fit strategy. Returns a plan dict; pure and testable.

    info: {"width", "height", ...} from ff.info(). Strategy is "noop", "pad",
    or "crop" (crop only when explicitly requested with a focus point).
    """
    platform, placement, spec = lookup(target, specs)
    sw, sh = int(info["width"]), int(info["height"])
    tw, th = spec["width"], spec["height"]
    match = aspect_matches(spec, sw, sh)
    min_ok = sw >= spec.get("min_width", 0) and sh >= spec.get("min_height", 0)
    if match and min_ok and not crop:
        return {"strategy": "noop", "platform": platform, "placement": placement,
                "spec": spec, "target_size": [tw, th],
                "reason": f"{sw}x{sh} already {spec['aspect']} "
                          f"({platform}:{placement}) — no conversion needed"}
    warnings = []
    if crop:
        (fx, fy), warnings = resolve_focus(focus, focus_x, focus_y,
                                           input_path=info.get("path"))
        rep = crop_report(sw, sh, tw, th, fx, fy)
        return {"strategy": "crop", "platform": platform, "placement": placement,
                "spec": spec, "target_size": [tw, th], "source_size": [sw, sh],
                "focus": [fx, fy],
                "warnings": warnings, "crop": rep,
                "reason": (f"{sw}x{sh} -> {tw}x{th} ({platform}:{placement}): "
                           f"CROP-TO-FILL ({rep['summary']}). Destructive — "
                           f"you approved this with --crop.")}
    return {"strategy": "pad", "platform": platform, "placement": placement,
            "spec": spec, "target_size": [tw, th],
            "reason": (f"{sw}x{sh} -> {tw}x{th} ({platform}:{placement}): "
                       f"PAD (blurred-background fill) — nothing is cut, "
                       f"100% of the source frame is preserved.")}


def build_pad(input_path, output_path, tw, th, strict=True):
    """Non-destructive fit: blurred-background fill to TWxTH."""
    ff._guard(input_path, output_path, strict)
    return [ff.FFMPEG, "-y", "-i", input_path, "-vf", ff.pad_filter(tw, th),
            "-c:v", "libx264", "-preset", "fast", "-crf", "19",
            "-c:a", "aac", output_path]


def build_crop_fill(input_path, output_path, tw, th, fx, fy, strict=True,
                    source_size=None):
    """Destructive cover-crop to TWxTH centered at focus (fx, fy).

    source_size (sw, sh) lets callers get concrete crop-box math without
    probing (dry-run previews). When omitted and the input exists, the file
    is probed; otherwise a generic cover-crop filtergraph is emitted.
    """
    ff._guard(input_path, output_path, strict)
    sw_sh = source_size
    if sw_sh is None and strict and os.path.exists(input_path):
        inf = ff.info(input_path)
        sw_sh = (inf["width"], inf["height"])
    if sw_sh is None:
        filt = (f"scale=iw*max({tw}/iw\\,{th}/ih):ih*max({tw}/iw\\,{th}/ih),"
                f"crop={tw}:{th},setsar=1,format=yuv420p")
    else:
        SW2, SH2, ox, oy = crop_box(sw_sh[0], sw_sh[1], tw, th, fx, fy)
        filt = (f"scale={SW2}:{SH2},crop={tw}:{th}:{ox}:{oy},"
                f"setsar=1,format=yuv420p")
    return [ff.FFMPEG, "-y", "-i", input_path, "-vf", filt,
            "-c:v", "libx264", "-preset", "fast", "-crf", "19",
            "-c:a", "aac", output_path]


def build_fit(input_path, output_path, fit_plan, strict=True):
    """Route a plan() result to the right builder."""
    tw, th = fit_plan["target_size"]
    strategy = fit_plan["strategy"]
    if strategy == "noop":
        raise ValueError("noop plan: no conversion needed — nothing to build")
    if strategy == "pad":
        return build_pad(input_path, output_path, tw, th, strict)
    if strategy == "crop":
        fx, fy = fit_plan["focus"]
        return build_crop_fill(input_path, output_path, tw, th, fx, fy, strict,
                               source_size=fit_plan.get("source_size"))
    raise ValueError(f"unknown strategy {strategy!r}")


# ------------------------------------------------------------- preflight ----

def preflight(info, target, specs=None):
    """Validate a probed file against a placement spec.

    Returns {"passed", "checks": [...], "fixes": [...], "advisories": [...]}.
    """
    platform, placement, spec = lookup(target, specs)
    tw, th = spec["width"], spec["height"]
    sw, sh = int(info.get("width") or 0), int(info.get("height") or 0)
    checks, fixes, advisories = [], [], []

    def add(name, ok, detail, fix=None, advisory=False):
        checks.append({"name": name, "ok": ok, "detail": detail})
        if not ok and fix:
            fixes.append(fix)
        if advisory:
            advisories.append(detail)

    fit_hint = (f"run `bin/social-agent video fit --input <file> "
                f"--output <fixed.mp4> --for {platform}:{placement}`")
    want = f"{spec['aspect']} ({tw}x{th})"
    if sw and sh:
        m = aspect_matches(spec, sw, sh)
        if m == "primary":
            add("aspect", True, f"{sw}x{sh} matches {want}")
        elif m == "alternate":
            add("aspect", True, f"{sw}x{sh} accepted (not the recommended {want})",
                advisory=True)
        else:
            add("aspect", False,
                f"{sw}x{sh} is not {want} for {platform}:{placement}",
                fix=f"aspect mismatch — {fit_hint}")
        if sw >= spec.get("min_width", 0) and sh >= spec.get("min_height", 0):
            rec = (f"{sw}x{sh} meets minimum "
                   f"{spec.get('min_width')}x{spec.get('min_height')}")
            if sw < tw or sh < th:
                add("resolution", True, rec + f" (below recommended {tw}x{th})",
                    advisory=True)
            else:
                add("resolution", True, f"{sw}x{sh} >= recommended {tw}x{th}")
        else:
            add("resolution", False,
                f"{sw}x{sh} below minimum "
                f"{spec.get('min_width')}x{spec.get('min_height')}",
                fix=f"resolution too low — upscale via {fit_hint}")
    else:
        add("aspect", False, "could not probe dimensions",
            fix="check the file is a readable video")

    dur = info.get("duration")
    if dur is not None:
        md = spec.get("max_duration")
        if md and dur > md:
            add("duration", False, f"{dur:.1f}s exceeds max {md}s for "
                f"{platform}:{placement}",
                fix=f"shorten the video (trim) before posting to {platform}:{placement}")
        else:
            add("duration", True, f"{dur:.1f}s within max {spec.get('max_duration')}s")

    size = info.get("file_size")
    if size is not None:
        cap = spec.get("max_size_mb", 0) * 1024 * 1024
        if cap and size > cap:
            add("file_size", False,
                f"{size / 1048576:.1f} MB exceeds {spec.get('max_size_mb')} MB cap",
                fix="re-encode smaller: `bin/social-agent video compress "
                    "--input <file> --output <small.mp4> --preset <platform>`")
        else:
            add("file_size", True,
                f"{size / 1048576:.1f} MB within {spec.get('max_size_mb')} MB cap")

    cont = (info.get("container") or "").lower().lstrip(".")
    if cont:
        allowed = [c.lower() for c in spec.get("containers", [])]
        if cont in allowed:
            add("container", True, f".{cont} accepted")
        else:
            add("container", False,
                f".{cont} not in accepted containers {allowed}",
                fix="re-wrap/re-encode to .mp4")

    vc = (info.get("vcodec") or "").lower()
    if vc:
        preferred = [c.lower() for c in spec.get("codecs", [])]
        if vc in preferred or vc == "avc":
            add("codec", True, f"{vc} accepted")
        else:
            add("codec", True, f"{vc} not the preferred codec {preferred} "
                "(platforms usually transcode — acceptable)",
                advisory=True)

    passed = all(c["ok"] for c in checks)
    return {"target": f"{platform}:{placement}", "passed": passed,
            "checks": checks, "fixes": fixes, "advisories": advisories}
