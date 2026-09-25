"""Tests for the core package: permanent memory, backups, recovery."""

import json
import os

from core import backup as backup_mod
from core import memory as mem_mod
from core import recovery as rec_mod


def test_memory_schema_and_round_trip(home):
    mem_mod.init_db(home)
    assert mem_mod.schema_version(home) == mem_mod.SCHEMA_VERSION
    a = mem_mod.upsert_account(home, "t1", "tiktok", handle="nova")
    assert a["label"] == "t1" and a["handle"] == "nova"
    v = mem_mod.set_brand_voice(home, "t1", tone_profile="bold",
                                banned=["ai-slop"], dos=["hook fast"])
    assert v["tone_profile"] == "bold"
    did = mem_mod.log_decision(home, "user", "post daily", "consistency")
    assert did == 1
    ds = mem_mod.list_decisions(home)
    assert ds[0]["summary"] == "post daily"
    sid, ver = mem_mod.sop_add(home, "weekly review", "# review\n1. check stats")
    assert ver == 1
    assert mem_mod.sop_get(home, sid)["title"] == "weekly review"


def test_memory_relations_and_graph(home):
    mem_mod.relate(home, "brand:nova", "owns", "account:t1")
    mem_mod.relate(home, "follower:ada", "frequent_customer_of", "brand:nova")
    mem_mod.relate(home, "hashtag:ai", "performs_well_on", "day:friday")
    mem_mod.relate(home, "video:v1", "belongs_to", "campaign:c1")
    edges = mem_mod.graph(home, "brand:nova")
    by_pred = {(e["subject"], e["predicate"], e["object"]) for e in edges}
    assert ("brand:nova", "owns", "account:t1") in by_pred
    assert ("follower:ada", "frequent_customer_of", "brand:nova") in by_pred
    # idempotent: relating twice does not duplicate
    mem_mod.relate(home, "brand:nova", "owns", "account:t1")
    assert len(mem_mod.graph(home, "brand:nova")) == 2


def test_memory_query_select_only(home):
    mem_mod.upsert_account(home, "t1", "tiktok")
    cols, rows = mem_mod.query_select(home, "SELECT label, platform FROM accounts")
    assert cols == ["label", "platform"]
    assert rows == [{"label": "t1", "platform": "tiktok"}]
    for bad in ("DELETE FROM accounts", "DROP TABLE accounts",
                "UPDATE accounts SET label='x'", "INSERT INTO accounts VALUES ('a')",
                "SELECT 1; DROP TABLE accounts"):
        try:
            mem_mod.query_select(home, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"non-SELECT accepted: {bad!r}")
    # multi-statement is refused
    try:
        mem_mod.query_select(home, "SELECT 1; SELECT 2")
    except ValueError:
        pass
    else:
        raise AssertionError("multi-statement SELECT accepted")


def test_people_migrate_legacy_json(home):
    legacy = os.path.join(home, "people")
    os.makedirs(legacy)
    with open(os.path.join(legacy, "t1.json"), "w", encoding="utf-8") as fh:
        json.dump({"ada": {"handle": "ada",
                           "counts": {"comment": 6, "like": 4},
                           "first_seen": "2026-01-01", "last_seen": "2026-02-02",
                           "tags": ["fan"], "notes": [],
                           "sentiments": [0.8], "last_text": "hi"}}, fh)
    from people import db as pdb
    rec = pdb.get(home, "t1", "ada")
    assert rec is not None
    assert rec["counts"]["comment"] == 6
    assert rec["tags"] == ["fan"]
    assert rec["score"] == 6 * 3 + 4 * 1
    # legacy dir moved aside, migration does not run twice
    assert not os.path.isdir(legacy)
    rec2 = pdb.get(home, "t1", "ada")
    assert rec2["score"] == rec["score"]


def test_people_scoring_unchanged(home):
    from people import db as pdb
    pdb.upsert(home, "t1", "bob", "comment")
    pdb.upsert(home, "t1", "bob", "comment")
    pdb.upsert(home, "t1", "bob", "like")
    rec = pdb.get(home, "t1", "bob")
    assert rec["counts"] == {"comment": 2, "like": 1, "dm": 0, "follow": 0,
                             "mention": 0}
    assert rec["score"] == 2 * 3 + 1
    top = pdb.top(home, "t1", n=5)
    assert top[0][0] == "bob"


def test_backup_snapshot_restore_dry_run(home):
    os.makedirs(home, exist_ok=True)
    with open(os.path.join(home, "queue.json"), "w") as fh:
        fh.write('[{"id": "q1"}]')
    m1 = backup_mod.snapshot(home, "manual", files=["queue.json"],
                             note="first")
    assert os.path.isfile(os.path.join(home, "backups", "manifests",
                                       m1["id"] + ".json"))
    with open(os.path.join(home, "queue.json"), "w") as fh:
        fh.write('[{"id": "q1"}, {"id": "q2"}]')
    m2 = backup_mod.snapshot(home, "manual", files=["queue.json"])
    d = backup_mod.diff(home, m1["id"], m2["id"])
    assert d["changed"] == ["queue.json"]
    # dry-run restore: plan only, live file untouched
    plan = backup_mod.restore(home, m1["id"], dry_run=True)
    assert any(c["action"] == "would-overwrite" for c in plan["changes"])
    with open(os.path.join(home, "queue.json")) as fh:
        assert '"q2"' in fh.read()
    # --apply stages, never overwrites
    plan2 = backup_mod.restore(home, m1["id"], dry_run=False)
    staged = os.path.join(plan2["staged_to"], "queue.json")
    assert os.path.isfile(staged)
    with open(staged) as fh:
        assert '"q2"' not in fh.read()
    with open(os.path.join(home, "queue.json")) as fh:
        assert '"q2"' in fh.read()  # live file still new


def test_backup_memory_incremental(home):
    mem_mod.init_db(home)
    mem_mod.upsert_account(home, "t1", "tiktok")
    # the write hook already snapshotted -> explicit call sees no change
    snaps = backup_mod.list_snapshots(home)
    assert any(m["trigger"] == "memory_updated" for m in snaps)
    id1, changed1 = backup_mod.snapshot_memory_incremental(home)
    assert changed1 is False
    # a mutation that bypasses the write hook -> new snapshot on next check
    cx = mem_mod.connect(home)
    cx.execute("INSERT INTO decisions (made_by, summary, rationale,"
               " created_at) VALUES (?, ?, ?, ?)",
               ("u", "s", "r", mem_mod.utcnow()))
    cx.commit()
    cx.close()
    id2, changed2 = backup_mod.snapshot_memory_incremental(home)
    assert changed2 is True and id2 != id1


def test_recovery_journal_idempotency(home):
    b = rec_mod.begin(home, "publish", "q1", {"platform": "tiktok"})
    assert b["duplicate"] is False
    rec_mod.end(home, b["id"], True, result="ok")
    b2 = rec_mod.begin(home, "publish", "q1", {"platform": "tiktok"})
    assert b2["duplicate"] is True  # same idempotency key: refuse repeat


def test_recovery_replay_skips_completed(home):
    # journal a publish intent, crash (no end), but the approval record
    # shows it actually completed -> recover must SKIP, never repeat
    b = rec_mod.begin(home, "publish", "q9", {"platform": "tiktok"})
    os.makedirs(os.path.join(home, "approvals"))
    with open(os.path.join(home, "approvals", "pending.json"), "w") as fh:
        json.dump([{"id": "ap1", "type": "publish", "status": "approved",
                    "ref": {"store": "queue.json", "id": "q9"}}], fh)
    report = rec_mod.recover(home)
    assert len(report["skipped_completed"]) == 1
    assert report["skipped_completed"][0]["target"] == "q9"
    # a second recover finds nothing unfinished (marked completed)
    report2 = rec_mod.recover(home)
    assert not report2["skipped_completed"]


def test_recovery_render_verify(home):
    os.makedirs(home, exist_ok=True)
    out = os.path.join(home, "v.mp4")
    with open(out, "wb") as fh:
        fh.write(b"x" * 100)
    b = rec_mod.begin(home, "render", "job1", {"output": out},
                      command="true")
    # output exists -> verified completed -> skipped, not re-executed
    report = rec_mod.recover(home, execute=True)
    assert len(report["skipped_completed"]) == 1
    os.remove(out)
    b2 = rec_mod.begin(home, "render", "job2", {"output": out},
                       command="true")
    report3 = rec_mod.recover(home, execute=True)
    resumed = [r for r in report3["resumed"] if r["target"] == "job2"]
    assert resumed and resumed[0].get("re_executed") is True


def test_recovery_stale_runner(home):
    rec_mod.mark_runner(home, cmd="watch --once")
    # current process is alive -> not stale
    assert rec_mod.stale_runner(home) is None
    # fake a dead pid
    with open(os.path.join(home, "audit", "runner.pid"), "w") as fh:
        json.dump({"pid": 99999999, "cmd": "watch", "started_at": "x",
                   "ts": 1}, fh)
    stale = rec_mod.stale_runner(home)
    assert stale is not None and "gone" in stale["reason"]
