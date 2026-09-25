"""Secondary (remote) backup layer: OPTIONAL, encrypted, consent-gated.

The agent is fully functional offline. Remote backup exists only if the
user chose a provider at install (or later via `backup remote-setup`)
AND granted explicit consent. There is no silent syncing: `backup sync`
is always a deliberate command (or a scheduler job the user created
themselves).

Security rules (fail-closed):
  * No consent recorded  -> sync REFUSED.
  * No encryption configured -> sync REFUSED (remote bundles are always
    encrypted; plaintext cookies/credentials never leave the machine).
  * The encryption key lives at backups/.remote_key (0600) — local only,
    never included in any bundle, never uploaded.
  * Encryption backend: `cryptography` (Fernet) if installed, else the
    `gpg` binary (symmetric AES256). Neither available -> refuse with
    install instructions (never roll our own crypto).

Providers: folder (external folder/drive), github, gdrive, onedrive,
dropbox, s3 (S3-compatible). Cloud drives go through rclone when it is
installed and configured; s3 needs boto3.
"""

import base64
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
from datetime import datetime, timezone

REMOTE_CONFIG = os.path.join("backups", "remote.json")
REMOTE_KEY = os.path.join("backups", ".remote_key")
BUNDLE_PREFIX = "social-agent-remote"

PROVIDERS = ("folder", "github", "gdrive", "onedrive", "dropbox", "s3")


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ----------------------------------------------------------------- config ---

def _config_path(home):
    return os.path.join(home, REMOTE_CONFIG)


def _key_path(home):
    return os.path.join(home, REMOTE_KEY)


def get_config(home):
    p = _config_path(home)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def setup(home, provider, target="", by="user"):
    """Record the user's provider choice. Consent is granted HERE,
    explicitly, at setup time — never implied."""
    if provider not in PROVIDERS and provider != "none":
        raise ValueError(f"unknown provider {provider!r}")
    cfg = {
        "provider": provider,
        "target": target,
        "consent": ({"granted_at": utcnow(), "by": by,
                     "provider": provider}
                    if provider != "none" else None),
        "encryption": None,
        "set_up_at": utcnow(),
    }
    if provider == "none":
        cfg["provider"] = None
    os.makedirs(os.path.dirname(_config_path(home)), exist_ok=True)
    tmp = _config_path(home) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
    os.replace(tmp, _config_path(home))
    return cfg


def revoke_consent(home):
    """Remove the provider choice entirely (back to offline-only)."""
    try:
        os.remove(_config_path(home))
    except OSError:
        pass
    return {"provider": None, "consent": None}


# -------------------------------------------------------------- encryption ---

def _fernet_backend():
    try:
        from cryptography.fernet import Fernet  # noqa
        return "cryptography"
    except ImportError:
        return None


def _gpg_backend():
    return "gpg" if shutil.which("gpg") else None


def encryption_backend():
    """Best available encryption backend, or None."""
    return _fernet_backend() or _gpg_backend()


def ensure_key(home):
    """Create the local encryption key if missing (0600, never uploaded)."""
    kp = _key_path(home)
    if os.path.exists(kp):
        return kp
    backend = encryption_backend()
    if backend is None:
        raise RuntimeError(
            "no encryption backend: install the `cryptography` Python"
            " package (`pip install cryptography`) or the `gpg` binary."
            " Remote sync stays disabled until then.")
    raw = os.urandom(32)
    with open(kp, "wb") as fh:
        fh.write(raw)
    os.chmod(kp, 0o600)
    cfg = get_config(home) or {}
    cfg["encryption"] = {"method": backend, "key_id": hashlib.sha256(
        raw).hexdigest()[:16], "created_at": utcnow()}
    tmp = _config_path(home) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
    os.replace(tmp, _config_path(home))
    return kp


def _encrypt_file(home, src_path, dest_path):
    """Encrypt src -> dest with the local key. Returns the method used."""
    kp = _key_path(home)
    if not os.path.exists(kp):
        raise RuntimeError("no encryption key — run `backup remote-setup`")
    with open(kp, "rb") as fh:
        key = fh.read()
    backend = encryption_backend()
    if backend == "cryptography":
        from cryptography.fernet import Fernet
        fkey = base64.urlsafe_b64encode(hashlib.sha256(
            b"social-agent-remote:" + key).digest())
        token = Fernet(fkey).encrypt(open(src_path, "rb").read())
        with open(dest_path, "wb") as fh:
            fh.write(b"SAR1:" + token)
        return "cryptography/fernet"
    if backend == "gpg":
        # passphrase via file descriptor; never on the command line
        pf = dest_path + ".pass"
        with open(pf, "wb") as fh:
            fh.write(base64.urlsafe_b64encode(key))
        os.chmod(pf, 0o600)
        try:
            proc = subprocess.run(
                ["gpg", "--batch", "--yes", "--pinentry-mode", "loopback",
                 "--passphrase-file", pf, "--symmetric",
                 "--cipher-algo", "AES256", "-o", dest_path, src_path],
                capture_output=True, text=True, timeout=300)
        finally:
            try:
                os.remove(pf)
            except OSError:
                pass
        if proc.returncode != 0:
            raise RuntimeError(f"gpg encryption failed: "
                               f"{proc.stderr[-300:]}")
        return "gpg/aes256"
    raise RuntimeError("no encryption backend available")


# ------------------------------------------------------------------ bundle ---

def build_bundle(home, snapshot_name="latest"):
    """Build the encrypted remote bundle from a versioned snapshot.

    The bundle contains ONLY the protected set (via the versioned
    snapshot's files/) — cache was already excluded at snapshot time,
    and the encryption key itself is never inside."""
    from core import backup as backup_mod
    if snapshot_name == "latest":
        snapshot_name = backup_mod.resolve_latest(home)
        if not snapshot_name:
            raise RuntimeError("no versioned snapshot to sync —"
                               " run `backup snapshot --versioned` first")
    src = os.path.join(home, "backups", snapshot_name)
    if not os.path.isdir(src):
        raise KeyError(f"unknown snapshot {snapshot_name!r}")
    tmpdir = tempfile.mkdtemp(prefix="sa-remote-")
    plain = os.path.join(tmpdir, "bundle.tar.gz")
    with tarfile.open(plain, "w:gz") as tar:
        tar.add(src, arcname=snapshot_name)
    enc = os.path.join(
        tmpdir, f"{BUNDLE_PREFIX}-{snapshot_name}-"
        f"{int(time.time())}.sar.enc")
    method = _encrypt_file(home, plain, enc)
    try:
        os.remove(plain)
    except OSError:
        pass
    return {"bundle": enc, "snapshot": snapshot_name, "method": method,
            "size": os.path.getsize(enc), "tmpdir": tmpdir}


# ---------------------------------------------------------------- providers ---

def _push_folder(home, bundle, cfg):
    target = os.path.expanduser(cfg.get("target") or "")
    if not target:
        raise RuntimeError("folder provider needs a target directory")
    os.makedirs(target, exist_ok=True)
    dest = os.path.join(target, os.path.basename(bundle))
    shutil.copyfile(bundle, dest)
    return {"ok": True, "detail": f"copied to {dest}"}


def _push_github(home, bundle, cfg):
    """Commit the bundle into a git repo at the target.

    target: local path (a git repo is init'd there) or owner/repo with
    `gh` authenticated — then we attempt `gh` upload via release asset.
    Push credentials are the USER's own (gh auth); the agent never
    stores tokens."""
    target = (cfg.get("target") or "").strip()
    if not target:
        raise RuntimeError("github provider needs a target"
                           " (local path or owner/repo)")
    if "/" in target and not os.path.exists(os.path.expanduser(target)) \
            and shutil.which("gh"):
        # owner/repo form with gh available: attach as a release asset
        rel = f"social-agent-backup-{int(time.time())}"
        proc = subprocess.run(
            ["gh", "release", "create", rel, bundle, "--repo", target,
             "--title", f"social-agent backup {rel}",
             "--notes", "Encrypted agent backup bundle."],
            capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            raise RuntimeError(f"gh release failed: {proc.stderr[-300:]}")
        return {"ok": True,
                "detail": f"uploaded as release asset {rel} on {target}"}
    repo = os.path.expanduser(target)
    os.makedirs(repo, exist_ok=True)
    if not os.path.isdir(os.path.join(repo, ".git")):
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True,
                       capture_output=True, timeout=60)
    dest = os.path.join(repo, os.path.basename(bundle))
    shutil.copyfile(bundle, dest)
    subprocess.run(["git", "add", os.path.basename(bundle)], cwd=repo,
                   check=True, capture_output=True, timeout=60)
    proc = subprocess.run(
        ["git", "-c", "user.name=social-agent",
         "-c", "user.email=social-agent@local",
         "commit", "-qm", f"encrypted backup {os.path.basename(bundle)}"],
        cwd=repo, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0 and "nothing to commit" not in (
            proc.stdout + proc.stderr):
        raise RuntimeError(f"git commit failed: {proc.stderr[-300:]}")
    return {"ok": True,
            "detail": f"committed in local git repo {repo}."
                      " Push it yourself (`git push`) — the agent never"
                      " holds your GitHub credentials."}


def _push_rclone(home, bundle, cfg, provider):
    if not shutil.which("rclone"):
        raise RuntimeError(
            f"{provider} sync needs rclone installed and configured"
            f" (`rclone config` a remote named e.g. '{provider}')."
            " See docs/dual-backup.md.")
    remote = cfg.get("target") or f"{provider}:social-agent-backups"
    dest = f"{remote}/{os.path.basename(bundle)}"
    proc = subprocess.run(["rclone", "copyto", bundle, dest],
                          capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"rclone failed: {proc.stderr[-300:]}")
    return {"ok": True, "detail": f"uploaded to {dest}"}


def _push_s3(home, bundle, cfg):
    try:
        import boto3  # noqa
    except ImportError:
        raise RuntimeError(
            "s3 sync needs boto3 (`pip install boto3`) and AWS credentials"
            " configured. See docs/dual-backup.md.")
    import boto3
    target = cfg.get("target") or ""
    # target form: s3://bucket/prefix  (credentials from the user's env)
    if not target.startswith("s3://"):
        raise RuntimeError("s3 target must look like s3://bucket/prefix")
    rest = target[5:]
    bucket, _, prefix = rest.partition("/")
    key = f"{prefix.rstrip('/')}/{os.path.basename(bundle)}" \
        if prefix else os.path.basename(bundle)
    boto3.client("s3").upload_file(bundle, bucket, key)
    return {"ok": True, "detail": f"uploaded to s3://{bucket}/{key}"}


_PUSHERS = {
    "folder": _push_folder,
    "github": _push_github,
    "gdrive": lambda h, b, c: _push_rclone(h, b, c, "gdrive"),
    "onedrive": lambda h, b, c: _push_rclone(h, b, c, "onedrive"),
    "dropbox": lambda h, b, c: _push_rclone(h, b, c, "dropbox"),
    "s3": _push_s3,
}


# --------------------------------------------------------------------- sync ---

def check_ready(home):
    """Fail-closed preflight for `backup sync`. Returns (ok, reasons)."""
    cfg = get_config(home)
    reasons = []
    if not cfg or not cfg.get("provider"):
        reasons.append("no remote provider configured"
                       " (`backup remote-setup`)")
    elif not (cfg.get("consent") or {}).get("granted_at"):
        reasons.append("no explicit user consent recorded")
    if not os.path.exists(_key_path(home)):
        reasons.append("no local encryption key (`backup remote-setup`)")
    elif encryption_backend() is None:
        reasons.append("no encryption backend (install `cryptography`"
                       " or `gpg`)")
    return (not reasons), reasons


def sync(home, snapshot_name="latest"):
    """Sync the latest versioned snapshot to the remote provider.

    Refuses (fail-closed) without consent + encryption. Never silent:
    this is only ever called from `backup sync` or an explicit
    scheduler job the user created."""
    ok, reasons = check_ready(home)
    if not ok:
        raise PermissionError("remote sync refused: "
                              + "; ".join(reasons))
    cfg = get_config(home)
    provider = cfg["provider"]
    pusher = _PUSHERS.get(provider)
    if pusher is None:
        raise ValueError(f"unknown provider {provider!r}")
    built = build_bundle(home, snapshot_name)
    try:
        result = pusher(home, built["bundle"], cfg)
    finally:
        shutil.rmtree(built["tmpdir"], ignore_errors=True)
    # record the sync in the audit trail
    log_path = os.path.join(home, "backups", "remote_sync.jsonl")
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "ts": utcnow(), "provider": provider,
            "snapshot": built["snapshot"], "method": built["method"],
            "size": built["size"], "result": result.get("detail", ""),
        }) + "\n")
    return {"provider": provider, "snapshot": built["snapshot"],
            "method": built["method"], "size": built["size"], **result}
