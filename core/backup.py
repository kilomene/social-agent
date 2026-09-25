"""Automatic backups: content-addressed snapshots ("git for the agent's life").

Layout under ``<home>/backups/``::

    manifests/<snap-id>.json      one manifest per snapshot
    blobs/xx/<sha256>             content-addressed file blobs (deduped)
    restore_staging/<snap-id>/    restore targets (never live files)

A manifest records: id, timestamp, trigger, note, parent snapshot,
per-file sha256s, and per-table memory hashes. Snapshots are cheap:
unchanged blobs are never copied twice.

Triggers (hooked into real code paths by bin/social-agent):
  post_created            new post drafted      -> version the draft/queue
  video_rendered          render finished       -> project + output manifest
  account_settings_changed accounts add/remove -> snapshot accounts.json
  memory_updated          any memory mutation  -> incremental (SQLite copy
                                                 + per-table hashes; skipped
                                                 when nothing changed)
  risky_action            before publish / mass hide / crisis off
                          -> recovery point

Retention (policy.yaml ``backups:``): keep the last N daily snapshots and
the last M hourly ones; unreferenced blobs are garbage-collected.

Restore NEVER overwrites live files: it stages everything under
restore_staging/<snap-id>/ and prints a plan. ``--dry-run`` (the default)
only prints the plan.
"""

import hashlib
import json
import os
import random
import shutil
import time
from datetime import datetime, timezone

BACKUP_DIR = "backups"
MANIFESTS = os.path.join(BACKUP_DIR, "manifests")
BLOBS = os.path.join(BACKUP_DIR, "blobs")
STAGING = os.path.join(BACKUP_DIR, "restore_staging")
LAST_MEMORY_HASH = os.path.join(BACKUP_DIR, ".last_memory_hash")

TRIGGERS = ("post_created", "video_rendered", "account_settings_changed",
            "memory_updated", "risky_action", "manual")


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"snap-{stamp}-{random.randrange(16 ** 6):06x}"


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _blob_path(home, digest):
    return os.path.join(home, BLOBS, digest[:2], digest)


def _store_blob(home, src_path):
    """Copy src into the content-addressed blob store; return its sha256."""
    digest = _sha256_file(src_path)
    dest = _blob_path(home, digest)
    if not os.path.exists(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = dest + ".tmp"
        shutil.copyfile(src_path, tmp)
        os.replace(tmp, dest)
    return digest


def _manifest_path(home, snap_id):
    return os.path.join(home, MANIFESTS, f"{snap_id}.json")


def _load_manifest(home, snap_id):
    p = _manifest_path(home, snap_id)
    if not os.path.exists(p):
        raise KeyError(f"unknown snapshot {snap_id!r}")
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def list_snapshots(home):
    d = os.path.join(home, MANIFESTS)
    if not os.path.isdir(d):
        return []
    out = []
    for f in sorted(os.listdir(d), reverse=True):
        if not f.endswith(".json"):
            continue
        try:
            with open(os.path.join(d, f), encoding="utf-8") as fh:
                m = json.load(fh)
            out.append(m)
        except (OSError, ValueError):
            continue
    return out


def latest_id(home):
    snaps = list_snapshots(home)
    return snaps[0]["id"] if snaps else None


def validate_snapshot(home, snap_id):
    """Is this snapshot structurally valid? (manifest parses, sane shape)."""
    try:
        m = _load_manifest(home, snap_id)
    except (KeyError, ValueError):
        return False, "manifest unreadable"
    if not isinstance(m.get("files"), list):
        return False, "manifest has no file list"
    if not m.get("timestamp"):
        return False, "manifest has no timestamp"
    return True, "ok"


def latest_valid_id(home):
    """Newest snapshot that passes validation (falls back past corrupt ones)."""
    for m in list_snapshots(home):
        ok, _ = validate_snapshot(home, m["id"])
        if ok:
            return m["id"]
    return None


# ------------------------------------------- versioned disaster snapshots ---

# Dual-backup architecture:
#   PRIMARY (local):  immutable versioned snapshots under backups/<ts>/,
#                     plus a `latest` pointer. No internet needed.
#   SECONDARY (remote): optional, encrypted, consent-gated (core/remote.py).

# Paths (home-relative) that are NEVER in a snapshot.
CACHE_EXCLUDES = (
    "cache/", "__pycache__/", ".pyc", ".tmp", ".DS_Store",
    # chromium profile internals that are pure cache
    "/Cache/", "/Code Cache/", "/GPUCache/", "/Service Worker/",
)

# The protected set: everything the agent must never lose.
# Video projects / editable assets are configurable via
# policy backups.include_projects (default True).
PROTECTED_PATHS = (
    "memory.db",                  # permanent memory (SQLite brain)
    "identity/identities.db",     # identity registry
    "identity/accounts/",         # per-account identity files
    "identity/host_sessions/",   # host-browser session records
    "identity/permissions/",      # per-identity grants
    "identity/fingerprints/",     # per-identity fingerprint notes
    "accounts/",                  # per-account files (personas, notes)
    "audit/journal.jsonl",        # event journal (source of truth)
    "missions/",                  # mission state files
    "policy/policy.yaml",         # behavior config
    "accounts.json",              # legacy account registry (if present)
)


def _is_excluded(rel_path):
    rp = rel_path.replace(os.sep, "/")
    for pat in CACHE_EXCLUDES:
        if pat.endswith("/"):
            if f"/{pat.strip('/')}/" in f"/{rp}/" or rp.startswith(pat):
                return True
        elif rp.endswith(pat):
            return True
    return False


def _iter_protected_files(home, include_projects=True):
    """Yield (home-relative path, absolute path) for the protected set."""
    for entry in PROTECTED_PATHS:
        apath = os.path.join(home, entry)
        if entry.endswith("/"):
            if not os.path.isdir(apath):
                continue
            for dp, dn, fn in os.walk(apath):
                # prune cache dirs inside the walk
                dn[:] = [d for d in dn
                         if not _is_excluded(
                             os.path.relpath(os.path.join(dp, d), home))]
                for f in sorted(fn):
                    rel = os.path.relpath(os.path.join(dp, f), home)
                    if _is_excluded(rel):
                        continue
                    yield rel, os.path.join(dp, f)
        else:
            if os.path.isfile(apath) and not _is_excluded(entry):
                yield entry, apath
    if include_projects:
        pdir = os.path.join(home, "projects")
        if os.path.isdir(pdir):
            for dp, dn, fn in os.walk(pdir):
                dn[:] = [d for d in dn
                         if not _is_excluded(
                             os.path.relpath(os.path.join(dp, d), home))]
                for f in sorted(fn):
                    rel = os.path.relpath(os.path.join(dp, f), home)
                    if _is_excluded(rel):
                        continue
                    yield rel, os.path.join(dp, f)


def versioned_snapshot_name(when=None):
    dt = when or datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%d_%H-%M")


def _latest_pointer(home):
    return os.path.join(home, BACKUP_DIR, "latest")


def resolve_latest(home):
    """Resolve the `latest` pointer to a versioned snapshot dir name."""
    p = _latest_pointer(home)
    if os.path.islink(p):
        target = os.readlink(p)
        name = os.path.basename(target.rstrip(os.sep))
        full = os.path.join(home, BACKUP_DIR, name)
        if os.path.isdir(full):
            return name
    if os.path.isdir(p) and not os.path.islink(p):
        # a real dir (older layout): treat as the latest snapshot itself
        return "latest"
    return None


def list_versioned(home):
    """All versioned snapshots, newest first."""
    root = os.path.join(home, BACKUP_DIR)
    if not os.path.isdir(root):
        return []
    out = []
    for name in sorted(os.listdir(root), reverse=True):
        if name in ("manifests", "blobs", "restore_staging", "latest"):
            continue
        full = os.path.join(root, name)
        man = os.path.join(full, "manifest.json")
        if os.path.isdir(full) and os.path.isfile(man):
            try:
                with open(man, encoding="utf-8") as fh:
                    out.append(json.load(fh))
            except (OSError, ValueError):
                continue
    return out


def versioned_snapshot(home, trigger="manual", note="", include_projects=True,
                       policy=None):
    """Take an immutable versioned snapshot: backups/<ts>/ + latest pointer.

    Copies the protected set (never cache/temp), writes manifest.json,
    and re-points `backups/latest`. Old versioned snapshots are never
    modified — restore picks any of them by timestamp."""
    if trigger not in TRIGGERS:
        raise ValueError(f"bad trigger {trigger!r}")
    if policy is not None:
        include_projects = (policy.get("backups") or {}).get(
            "include_projects", include_projects)
    name = versioned_snapshot_name()
    dest = os.path.join(home, BACKUP_DIR, name)
    # timestamp collision (two snapshots in one minute): suffix
    suffix = 0
    while os.path.exists(dest):
        suffix += 1
        dest = os.path.join(home, BACKUP_DIR, f"{name}-{suffix:02d}")
    name = os.path.basename(dest)
    os.makedirs(dest, exist_ok=True)
    files = []
    for rel, apath in _iter_protected_files(home, include_projects):
        target = os.path.join(dest, "files", rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(apath, target)
        files.append({"path": rel, "sha256": _sha256_file(target),
                      "size": os.path.getsize(target)})
    try:
        from core import memory as memory_mod
        tables = memory_mod.table_hashes(home)
    except Exception:  # noqa: BLE001 - snapshot must not fail on hashing
        tables = {}
    manifest = {
        "id": name, "timestamp": utcnow(), "trigger": trigger,
        "note": note, "files": files, "memory_tables": tables,
        "versioned": True, "include_projects": include_projects,
    }
    with open(os.path.join(dest, "manifest.json"), "w",
              encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    # re-point latest (symlink; atomic replace)
    link = _latest_pointer(home)
    tmp_link = link + ".tmp"
    try:
        if os.path.islink(tmp_link) or os.path.exists(tmp_link):
            os.remove(tmp_link)
        os.symlink(name, tmp_link)
        os.replace(tmp_link, link)
    except OSError:
        # filesystems without symlink support: record the name in a file
        with open(os.path.join(home, BACKUP_DIR, "latest.txt"), "w",
                   encoding="utf-8") as fh:
            fh.write(name)
    return manifest


def versioned_restore_plan(home, name):
    """What would restoring versioned snapshot <name> change? Dry-run."""
    if name == "latest":
        name = resolve_latest(home)
        if not name:
            raise KeyError("no latest snapshot")
    dest = os.path.join(home, BACKUP_DIR, name)
    man_path = os.path.join(dest, "manifest.json")
    if not os.path.isfile(man_path):
        raise KeyError(f"unknown versioned snapshot {name!r}")
    with open(man_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    plan = []
    for f in manifest.get("files", []):
        src = os.path.join(dest, "files", f["path"])
        if not os.path.isfile(src):
            plan.append({"path": f["path"], "action": "skip-missing-in-snap"})
            continue
        apath = os.path.join(home, f["path"])
        current = _sha256_file(apath) if os.path.isfile(apath) else None
        if current == f["sha256"]:
            plan.append({"path": f["path"], "action": "unchanged"})
        elif current is None:
            plan.append({"path": f["path"], "action": "would-create"})
        else:
            plan.append({"path": f["path"], "action": "would-overwrite"})
    return {"snapshot": name, "timestamp": manifest.get("timestamp"),
            "trigger": manifest.get("trigger"), "note": manifest.get("note"),
            "changes": plan}


def versioned_restore(home, name, dry_run=True):
    """Restore a versioned snapshot. dry_run=True (default): plan only.
    dry_run=False: stage into backups/restore_staging/<name>/ (never live)."""
    if name == "latest":
        name = resolve_latest(home)
        if not name:
            raise KeyError("no latest snapshot")
    plan = versioned_restore_plan(home, name)
    if dry_run:
        return plan
    dest = os.path.join(home, BACKUP_DIR, name)
    stage = os.path.join(home, STAGING, name)
    os.makedirs(stage, exist_ok=True)
    with open(os.path.join(dest, "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    for f in manifest.get("files", []):
        src = os.path.join(dest, "files", f["path"])
        if not os.path.isfile(src):
            continue
        target = os.path.join(stage, f["path"])
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(src, target)
    plan["staged_to"] = stage
    return plan


# ------------------------------------------------------- export / import ---

def export_backup(home, name, dest_path):
    """Export a versioned snapshot as a portable .tar.gz bundle.

    The bundle imports cleanly into a fresh install on another VM."""
    import tarfile
    if name == "latest":
        name = resolve_latest(home)
        if not name:
            raise KeyError("no latest snapshot")
    src = os.path.join(home, BACKUP_DIR, name)
    if not os.path.isdir(os.path.join(src, "manifest.json")) and \
            not os.path.isfile(os.path.join(src, "manifest.json")):
        raise KeyError(f"unknown versioned snapshot {name!r}")
    dest_path = os.path.expanduser(dest_path)
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    with tarfile.open(dest_path, "w:gz") as tar:
        tar.add(src, arcname=name)
    return {"snapshot": name, "bundle": dest_path,
            "size": os.path.getsize(dest_path)}


def import_backup(home, bundle_path, force=False):
    """Import a portable bundle into this home (fresh installs welcome).

    Extracts to a staging dir, validates the manifest, then installs the
    snapshot's files into the home tree. Refuses to overwrite existing
    protected files without force=True."""
    import tarfile
    bundle_path = os.path.expanduser(bundle_path)
    if not os.path.isfile(bundle_path):
        raise KeyError(f"bundle not found: {bundle_path!r}")
    stage = os.path.join(home, BACKUP_DIR, "import_staging")
    if os.path.isdir(stage):
        shutil.rmtree(stage)
    os.makedirs(stage, exist_ok=True)
    with tarfile.open(bundle_path, "r:gz") as tar:
        # safety: refuse absolute paths / path traversal in the bundle
        for m in tar.getmembers():
            if m.name.startswith(("/", "..")) or "/../" in m.name:
                raise ValueError(f"unsafe bundle member {m.name!r}")
        tar.extractall(stage)
    # find the snapshot dir (single top-level dir with manifest.json)
    snap_dir = None
    for entry in os.listdir(stage):
        cand = os.path.join(stage, entry)
        if os.path.isdir(cand) and os.path.isfile(
                os.path.join(cand, "manifest.json")):
            snap_dir = cand
            break
    if snap_dir is None:
        raise ValueError("bundle contains no valid snapshot")
    with open(os.path.join(snap_dir, "manifest.json"),
              encoding="utf-8") as fh:
        manifest = json.load(fh)
    if not isinstance(manifest.get("files"), list):
        raise ValueError("bundle manifest is corrupt")
    installed, skipped = [], []
    files_root = os.path.join(snap_dir, "files")
    for f in manifest["files"]:
        src = os.path.join(files_root, f["path"])
        if not os.path.isfile(src):
            skipped.append(f["path"])
            continue
        # never let an import write outside the home tree
        dest = os.path.normpath(os.path.join(home, f["path"]))
        if not dest.startswith(os.path.normpath(home) + os.sep):
            skipped.append(f["path"])
            continue
        if os.path.exists(dest) and not force:
            skipped.append(f["path"] + " (exists)")
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(src, dest)
        installed.append(f["path"])
    shutil.rmtree(stage, ignore_errors=True)
    return {"snapshot": manifest.get("id"), "installed": installed,
            "skipped": skipped}


def snapshot(home, trigger, files=(), note="", memory_tables=None):
    """Take a snapshot. ``files`` are home-relative (or absolute) paths;
    missing files are recorded as absent, never an error."""
    if trigger not in TRIGGERS:
        raise ValueError(f"bad trigger {trigger!r}")
    os.makedirs(os.path.join(home, MANIFESTS), exist_ok=True)
    file_entries = []
    for f in files:
        apath = f if os.path.isabs(f) else os.path.join(home, f)
        if os.path.isfile(apath):
            digest = _store_blob(home, apath)
            file_entries.append({"path": f, "sha256": digest,
                                 "size": os.path.getsize(apath)})
        else:
            file_entries.append({"path": f, "sha256": None, "size": 0,
                                 "absent": True})
    parent = latest_id(home)
    snap_id = new_id()
    manifest = {
        "id": snap_id, "timestamp": utcnow(), "trigger": trigger,
        "note": note, "parent": parent, "files": file_entries,
        "memory_tables": memory_tables,
    }
    tmp = _manifest_path(home, snap_id) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    os.replace(tmp, _manifest_path(home, snap_id))
    enforce_retention(home)
    return manifest


def snapshot_memory_incremental(home):
    """Incremental memory backup: snapshot only when table hashes changed.

    Returns (snapshot_id, changed: bool)."""
    from core import memory as memory_mod
    tables = memory_mod.table_hashes(home)
    fingerprint = hashlib.sha256(
        json.dumps(tables, sort_keys=True).encode()).hexdigest()
    last = None
    if os.path.exists(os.path.join(home, LAST_MEMORY_HASH)):
        with open(os.path.join(home, LAST_MEMORY_HASH),
                  encoding="utf-8") as fh:
            last = fh.read().strip()
    if last == fingerprint:
        return latest_id(home), False
    db = memory_mod.db_path(home)
    manifest = snapshot(home, "memory_updated", files=[db],
                        note="incremental memory backup",
                        memory_tables=tables)
    with open(os.path.join(home, LAST_MEMORY_HASH), "w",
              encoding="utf-8") as fh:
        fh.write(fingerprint)
    return manifest["id"], True


def recovery_point(home, note=""):
    """Snapshot before a risky action (publish, mass hide, crisis off)."""
    return snapshot(
        home, "risky_action",
        files=["queue.json", "approvals/pending.json", "accounts.json",
               "crisis/crisis.json", "memory.db"],
        note=note or "recovery point before risky action")


def enforce_retention(home, keep_daily=7, keep_hourly=24, policy=None):
    """Prune manifests outside retention; garbage-collect orphan blobs."""
    if policy:
        keep_daily = (policy.get("backups") or {}).get("keep_daily",
                                                       keep_daily)
        keep_hourly = (policy.get("backups") or {}).get("keep_hourly",
                                                       keep_hourly)
    snaps = list_snapshots(home)
    keep = set()
    # newest-first: first `keep_hourly` are hourly keeps
    for m in snaps[:keep_hourly]:
        keep.add(m["id"])
    # then one per calendar day for keep_daily days
    seen_days = set()
    for m in snaps:
        day = m["timestamp"][:10]
        if day not in seen_days and len(seen_days) < keep_daily:
            seen_days.add(day)
            keep.add(m["id"])
    for m in snaps:
        if m["id"] not in keep:
            try:
                os.remove(_manifest_path(home, m["id"]))
            except OSError:
                pass
    # garbage-collect blobs no manifest references
    referenced = set()
    for m in list_snapshots(home):
        for f in m.get("files", []):
            if f.get("sha256"):
                referenced.add(f["sha256"])
    blob_root = os.path.join(home, BLOBS)
    if os.path.isdir(blob_root):
        for sub in os.listdir(blob_root):
            subdir = os.path.join(blob_root, sub)
            if not os.path.isdir(subdir):
                continue
            for blob in os.listdir(subdir):
                if blob not in referenced and len(blob) == 64:
                    try:
                        os.remove(os.path.join(subdir, blob))
                    except OSError:
                        pass
    return {"kept": len(keep), "pruned": len(snaps) - len(keep)}


def diff(home, id1, id2):
    """Compare two snapshots: added/removed/changed files + memory tables."""
    m1, m2 = _load_manifest(home, id1), _load_manifest(home, id2)
    f1 = {f["path"]: f.get("sha256") for f in m1.get("files", [])}
    f2 = {f["path"]: f.get("sha256") for f in m2.get("files", [])}
    added = [p for p in f2 if p not in f1]
    removed = [p for p in f1 if p not in f2]
    changed = [p for p in f2 if p in f1 and f1[p] != f2[p]]
    t1, t2 = m1.get("memory_tables") or {}, m2.get("memory_tables") or {}
    tables_changed = [t for t in t2
                      if t1.get(t, {}).get("sha256") != t2[t].get("sha256")]
    return {"from": id1, "to": id2, "trigger_from": m1.get("trigger"),
            "trigger_to": m2.get("trigger"), "added": added,
            "removed": removed, "changed": changed,
            "memory_tables_changed": tables_changed}


def restore_plan(home, snap_id):
    """Compute what a restore WOULD change. Pure planning, no writes."""
    m = _load_manifest(home, snap_id)
    plan = []
    for f in m.get("files", []):
        if f.get("absent") or not f.get("sha256"):
            plan.append({"path": f["path"], "action": "skip-absent-in-snapshot"})
            continue
        apath = f["path"] if os.path.isabs(f["path"]) \
            else os.path.join(home, f["path"])
        current = _sha256_file(apath) if os.path.isfile(apath) else None
        if current == f["sha256"]:
            plan.append({"path": f["path"], "action": "unchanged"})
        elif current is None:
            plan.append({"path": f["path"], "action": "would-create"})
        else:
            plan.append({"path": f["path"], "action": "would-overwrite",
                         "current_sha256": current[:12],
                         "snapshot_sha256": f["sha256"][:12]})
    return {"snapshot": snap_id, "timestamp": m.get("timestamp"),
            "trigger": m.get("trigger"), "note": m.get("note"),
            "changes": plan}


def restore(home, snap_id, dry_run=True):
    """Restore a snapshot — always staged, never overwriting live files.

    dry_run=True (default): return the plan only.
    dry_run=False: copy snapshot blobs into
    ``backups/restore_staging/<snap_id>/`` (mirroring home-relative paths)
    and write RESTORE_PLAN.md there. The operator copies files into place.
    """
    plan = restore_plan(home, snap_id)
    if dry_run:
        return plan
    m = _load_manifest(home, snap_id)
    stage = os.path.join(home, STAGING, snap_id)
    os.makedirs(stage, exist_ok=True)
    for f in m.get("files", []):
        if f.get("absent") or not f.get("sha256"):
            continue
        blob = _blob_path(home, f["sha256"])
        if not os.path.exists(blob):
            continue
        if os.path.isabs(f["path"]):
            dest = os.path.join(stage, "external",
                                f["path"].lstrip(os.sep))
        else:
            dest = os.path.join(stage, f["path"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(blob, dest)
    with open(os.path.join(stage, "RESTORE_PLAN.md"), "w",
              encoding="utf-8") as fh:
        fh.write(f"# Restore plan for {snap_id}\n\n")
        fh.write(f"Snapshot: {m.get('timestamp')} (trigger: {m.get('trigger')})\n")
        fh.write(f"Note: {m.get('note') or '-'}\n\n")
        fh.write("Staged files mirror the home directory layout (absolute\n"
                 "paths under `external/`). To apply: copy each file from\n"
                 "this staging dir into place, then delete the staging dir.\n\n")
        for c in plan["changes"]:
            fh.write(f"- {c['action']}: {c['path']}\n")
    plan["staged_to"] = stage
    return plan
