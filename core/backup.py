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
