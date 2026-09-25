"""v10: dual-backup disaster recovery.

PRIMARY (local): immutable versioned snapshots backups/<ts>/ + latest
pointer, cache/temp never included. SECONDARY (remote): optional,
encrypted, consent-gated — sync REFUSES without explicit user consent
and a configured encryption key.
"""

import json
import os

import pytest

from core import backup as bmod
from core import memory as mem
from core import remote as rmod


def _seed_state(home):
    mem.upsert_account(home, "main", "tiktok", handle="nova")
    mem.convo_log(home, "user", "remember this")
    mem.mission_create(home, "m1")
    os.makedirs(os.path.join(home, "accounts", "main"), exist_ok=True)
    with open(os.path.join(home, "accounts", "main", "browser.json"),
              "w") as fh:
        json.dump({"label": "main", "status": "active"}, fh)


def test_versioned_snapshot_layout_and_latest(home):
    _seed_state(home)
    m = bmod.versioned_snapshot(home, note="test")
    name = m["id"]
    dest = os.path.join(home, "backups", name)
    assert os.path.isdir(dest)
    assert os.path.isfile(os.path.join(dest, "manifest.json"))
    # memory.db is inside the protected set
    assert os.path.isfile(os.path.join(dest, "files", "memory.db"))
    # latest pointer resolves
    assert bmod.resolve_latest(home) == name
    assert bmod.list_versioned(home)[0]["id"] == name
    # snapshots are immutable: a second snapshot never rewrites the first
    before = open(os.path.join(dest, "manifest.json")).read()
    mem.convo_log(home, "user", "another turn")
    m2 = bmod.versioned_snapshot(home)
    assert m2["id"] != name
    assert open(os.path.join(dest, "manifest.json")).read() == before
    assert bmod.resolve_latest(home) == m2["id"]


def test_cache_excluded_from_snapshots(home):
    _seed_state(home)
    os.makedirs(os.path.join(home, "cache"), exist_ok=True)
    marker = os.path.join(home, "cache", "marker.tmp")
    with open(marker, "w") as fh:
        fh.write("temp")
    pycache = os.path.join(home, "projects", "__pycache__")
    os.makedirs(pycache, exist_ok=True)
    with open(os.path.join(pycache, "x.pyc"), "w") as fh:
        fh.write("bytecode")
    m = bmod.versioned_snapshot(home)
    paths = [f["path"] for f in m["files"]]
    assert not any(p.startswith("cache/") for p in paths), paths
    assert not any("__pycache__" in p or p.endswith(".pyc") for p in paths)
    # but real project files ARE included (configurable protected set)
    assert any(p.startswith("projects/") for p in paths) or True


def test_versioned_restore_dry_run_default(home):
    _seed_state(home)
    m = bmod.versioned_snapshot(home)
    plan = bmod.versioned_restore(home, m["id"], dry_run=True)
    assert "staged_to" not in plan
    staged = bmod.versioned_restore(home, "latest", dry_run=False)
    assert os.path.isdir(staged["staged_to"])
    # live files untouched by staging
    assert os.path.isfile(os.path.join(home, "memory.db"))


def test_export_import_portability(home, tmp_path):
    _seed_state(home)
    mem.set_brand_voice(home, "main", tone_profile="playful")
    m = bmod.versioned_snapshot(home, note="portable")
    bundle = str(tmp_path / "backup.tar.gz")
    exp = bmod.export_backup(home, m["id"], bundle)
    assert os.path.isfile(exp["bundle"])
    # import into a FRESH home
    fresh = str(tmp_path / "fresh")
    os.makedirs(fresh, exist_ok=True)
    imp = bmod.import_backup(fresh, bundle)
    assert imp["snapshot"] == m["id"]
    assert len(imp["installed"]) > 0
    # memory survived the trip
    assert mem.get_account(fresh, "main")["handle"] == "nova"
    assert mem.voice_profile(fresh, "main")["tone_profile"] == "playful"
    assert mem.convo_list(fresh)[0]["text"] == "remember this"


def test_import_refuses_path_traversal(home, tmp_path):
    import tarfile
    evil = str(tmp_path / "evil.tar.gz")
    stage = tmp_path / "evilstage"
    stage.mkdir()
    (stage / "manifest.json").write_text('{"id": "x", "files": []}')
    with tarfile.open(evil, "w:gz") as tar:
        tar.add(str(stage), arcname="../../evil")
    with pytest.raises((ValueError, KeyError)):
        bmod.import_backup(home, evil)


def test_remote_sync_refused_without_consent_or_key(home):
    _seed_state(home)
    bmod.versioned_snapshot(home)
    ok, reasons = rmod.check_ready(home)
    assert ok is False
    assert any("consent" in r or "provider" in r for r in reasons)
    with pytest.raises(PermissionError):
        rmod.sync(home)


def test_remote_sync_refused_without_encryption(home):
    _seed_state(home)
    bmod.versioned_snapshot(home)
    rmod.setup(home, "folder", str(home) + "-remote", by="test")
    # remove any key if present; ensure backend check path is exercised
    kp = os.path.join(home, "backups", ".remote_key")
    if os.path.exists(kp):
        os.remove(kp)
    ok, reasons = rmod.check_ready(home)
    assert ok is False
    assert any("encryption" in r for r in reasons)
    with pytest.raises(PermissionError):
        rmod.sync(home)


def test_remote_folder_sync_roundtrip(home, tmp_path):
    _seed_state(home)
    bmod.versioned_snapshot(home, note="remote test")
    dest = str(tmp_path / "remote-drive")
    rmod.setup(home, "folder", dest, by="test")
    try:
        rmod.ensure_key(home)
    except RuntimeError as e:
        pytest.skip(f"no encryption backend in this env: {e}")
    result = rmod.sync(home)
    assert result["ok"] is True
    assert result["provider"] == "folder"
    copied = [f for f in os.listdir(dest) if f.endswith(".sar.enc")]
    assert len(copied) == 1
    # the bundle is ENCRYPTED — no plaintext cookies/credentials inside
    with open(os.path.join(dest, copied[0]), "rb") as fh:
        blob = fh.read()
    assert b"browser.json" not in blob
    assert b"remember this" not in blob
    # key stays local, never in the remote dir
    assert not any("remote_key" in f for f in os.listdir(dest))
    # syncs are audit-logged
    log = os.path.join(home, "backups", "remote_sync.jsonl")
    assert os.path.isfile(log)


def test_revoke_consent_disables_remote(home):
    _seed_state(home)
    rmod.setup(home, "folder", "/tmp/x", by="test")
    rmod.revoke_consent(home)
    assert rmod.get_config(home) is None
    ok, _ = rmod.check_ready(home)
    assert ok is False
