"""v10: memory is the center of the system.

Schema v2 adds: conversations, browser_sessions, missions,
actions_ledger, scheduler_jobs, analytics — plus deepened brand voice
(examples + learned style rules). All state the resume engine needs to
continue exactly where the agent stopped.
"""

import pytest

from core import memory as mem


def test_schema_v3_migrates_cleanly(home):
    mem.init_db(home)
    assert mem.schema_version(home) == 4  # v3 + dm_agent_state
    # re-running is idempotent
    mem.init_db(home)
    assert mem.schema_version(home) == 4
    # the dm_agent_state table exists with its key columns
    cx = mem.connect(home)
    try:
        cols = [r[1] for r in cx.execute(
            "PRAGMA table_info(dm_agent_state)").fetchall()]
    finally:
        cx.close()
    for col in ("platform", "account_label", "thread_id", "last_seen_id",
                "last_inbound_at", "active", "pending_check", "idle_parked"):
        assert col in cols


def test_conversation_log_and_list(home):
    cid = mem.convo_log(home, "user", "launch the tiktok series")
    assert cid > 0
    mem.convo_log(home, "agent", "on it — drafting 3 hooks",
                  mission_id=1, kind="note")
    items = mem.convo_list(home)
    assert [i["role"] for i in items] == ["user", "agent"]
    assert items[0]["text"] == "launch the tiktok series"
    with pytest.raises(ValueError):
        mem.convo_log(home, "user", "   ")
    with pytest.raises(ValueError):
        mem.convo_log(home, "bot", "nope")


def test_mission_lifecycle(home):
    m = mem.mission_create(home, "launch-week", mission_type="growth",
                           account_label="main",
                           spec={"platforms": ["tiktok"]})
    assert m["status"] == "pending"
    assert m["spec"] == {"platforms": ["tiktok"]}
    # duplicate create is idempotent (no second row)
    mem.mission_create(home, "launch-week")
    assert len(mem.mission_list(home)) == 1
    mem.mission_set_status(home, "launch-week", "active")
    assert mem.mission_get(home, "launch-week")["status"] == "active"
    pending = mem.mission_pending(home)
    assert [p["name"] for p in pending] == ["launch-week"]
    mem.mission_set_status(home, "launch-week", "completed",
                           result={"posts": 5})
    assert mem.mission_pending(home) == []
    assert mem.mission_get(home, "launch-week")["result"] == {"posts": 5}
    with pytest.raises(ValueError):
        mem.mission_set_status(home, "launch-week", "bogus")


def test_actions_ledger_idempotent(home):
    mem.ledger_record(home, "key-1", "publish_post", target="vid9",
                      payload={"text": "hi"}, mission_id=3)
    # same key twice: no duplicate row, still exactly one
    mem.ledger_record(home, "key-1", "publish_post", target="vid9")
    assert mem.ledger_completed_keys(home) == {"key-1"}
    rec = mem.ledger_get(home, "key-1")
    assert rec["mission_id"] == 3
    assert rec["payload"] == {"text": "hi"}
    rows = mem.ledger_list(home)
    assert len(rows) == 1
    with pytest.raises(ValueError):
        mem.ledger_record(home, "", "publish_post")


def test_browser_session_registry(home):
    s = mem.session_register(home, "main", "/prof/main", "tiktok",
                             identity_id="nova")
    assert s["status"] == "new"
    assert s["identity_id"] == "nova"
    mem.session_set_status(home, "main", "active")
    assert mem.session_get(home, "main")["status"] == "active"
    mem.session_health(home, "main", ok=True)
    assert "ok" in mem.session_get(home, "main")["last_health_check"]
    mem.session_health(home, "main", ok=False, note="login wall")
    assert mem.session_get(home, "main")["status"] == "expired"
    with pytest.raises(ValueError):
        mem.session_set_status(home, "main", "bogus")


def test_scheduler_jobs_crud(home):
    j = mem.sched_add(home, "nightly", "interval", "3600",
                      {"action": "snapshot"})
    assert j["status"] == "enabled"
    assert j["next_run"] is not None
    assert j["payload"] == {"action": "snapshot"}
    # duplicate add is idempotent
    mem.sched_add(home, "nightly", "interval", "3600")
    assert len(mem.sched_list(home)) == 1
    due = mem.sched_due(home, now_iso="2999-01-01T00:00:00+00:00")
    assert [d["name"] for d in due] == ["nightly"]
    mem.sched_set(home, "nightly", status="disabled")
    assert mem.sched_due(home, now_iso="2999-01-01T00:00:00+00:00") == []
    mem.sched_set(home, "nightly", status="enabled")
    before = mem.sched_get(home, "nightly")["run_count"]
    mem.sched_mark_ran(home, "nightly")
    after = mem.sched_get(home, "nightly")
    assert after["run_count"] == before + 1
    assert after["last_run"] is not None
    with pytest.raises(ValueError):
        mem.sched_add(home, "bad", "cron", "* * *")


def test_analytics_rollups(home):
    mem.analytics_log(home, "tiktok", "followers", 1000, period="2026-09-25")
    mem.analytics_log(home, "tiktok", "followers", 1050, period="2026-09-25")
    mem.analytics_log(home, "youtube", "subs", 50)
    rows = mem.analytics_summary(home)
    tiktok = [r for r in rows
              if r["platform"] == "tiktok" and r["metric"] == "followers"]
    assert len(tiktok) == 1
    assert tiktok[0]["value"] == 1050  # latest wins
    yt = mem.analytics_summary(home, platform="youtube")
    assert len(yt) == 1 and yt[0]["value"] == 50


def test_brand_voice_deepening(home):
    mem.set_brand_voice(home, "main", tone_profile="playful")
    v = mem.voice_learn_example(home, "main", "no cap, this edit goes hard",
                                kind="post")
    assert len(v["examples"]) == 1
    assert v["examples"][0]["text"] == "no cap, this edit goes hard"
    # duplicate example text is not stored twice
    mem.voice_learn_example(home, "main", "no cap, this edit goes hard")
    assert len(mem.voice_profile(home, "main")["examples"]) == 1
    v = mem.voice_learn_rule(home, "main",
                             "never start a caption with 'hey guys'")
    assert v["style_rules"][0]["rule"] == \
        "never start a caption with 'hey guys'"
    assert v["tone_profile"] == "playful"  # base voice preserved
    assert v["last_trained"] is not None
    with pytest.raises(ValueError):
        mem.voice_learn_example(home, "main", "  ")


def test_hashed_tables_cover_v2(home):
    mem.convo_log(home, "user", "hi")
    mem.mission_create(home, "m1")
    hashes = mem.table_hashes(home)
    for t in ("conversations", "missions", "actions_ledger",
              "scheduler_jobs", "analytics", "browser_sessions"):
        assert t in hashes
        assert hashes[t]["rows"] >= 0
