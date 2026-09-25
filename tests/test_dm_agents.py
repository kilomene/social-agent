"""DM agent subsystem tests.

Covers: last_seen_id persistence across simulated restarts, per-thread
tracking, thread-id normalization (bare vs suffixed display ids resolve to
one merged row), duplicate guard, style gate, stop conditions, TikTok adapter
refusal, dm_check/dm_send ticket issuance with receipts, poll-interval
floor, trigger queue-jumping with the pile-up guard, and the credential
tripwire (no secrets in dm_agents code, state, or tickets).
"""

import json
import os
import re
import time

import pytest

from dm_agents import get_adapter, SUPPORTED
from dm_agents import state as dm_state
from dm_agents import style as style_mod
from dm_agents import replier as replier_mod
from dm_agents.agent import (DMAgent, POLL_INTERVAL_MIN,
                             POLL_INTERVAL_DEFAULT,
                             TARGET_INTERVAL_ASPIRATION)
from dm_agents.platforms import tiktok as tiktok_adapter
from hands import tickets as tickets_mod
from hands import steps as steps_mod
from approvals import queue as aq


# ------------------------------------------------------------- helpers ---

def _agent(home, platform="x", account="main", **cfg):
    return DMAgent(home, platform, account, config=cfg)


def _start(home, platform="x", account="main", **cfg):
    a = _agent(home, platform, account, **cfg)
    a.start()
    return a


def _msgs(*items):
    """Build observed-messages JSON: (thread, id, frm, text, ts) tuples."""
    threads = {}
    for tid, mid, frm, text, ts in items:
        threads.setdefault(tid, []).append(
            {"id": mid, "from": frm, "text": text, "ts": ts})
    return {"threads": [{"thread_id": t, "messages": m}
                        for t, m in threads.items()]}


# --------------------------------------------------------------- state ---

def test_last_seen_persists_across_restart(home):
    a = _start(home)
    dm_state.set_last_seen(home, "x", "main", "conv-1", "m9",
                           last_inbound_id="m9", last_inbound_ts=123.0)
    # "restart": brand-new agent object, same home dir
    b = DMAgent(home, "x", "main")
    assert dm_state.get_last_seen(home, "x", "main", "conv-1") == "m9"
    row = dm_state.get_thread(home, "x", "main", "conv-1")
    assert row["last_inbound_at"] == 123.0
    assert b.status()["threads"][0]["last_seen_id"] == "m9"


def test_per_thread_tracking_multiple_threads(home):
    a = _start(home)
    dm_state.set_last_seen(home, "x", "main", "conv-1", "m1")
    dm_state.set_last_seen(home, "x", "main", "conv-2", "m7")
    dm_state.set_last_seen(home, "x", "main", "conv-1", "m2")
    assert dm_state.get_last_seen(home, "x", "main", "conv-1") == "m2"
    assert dm_state.get_last_seen(home, "x", "main", "conv-2") == "m7"


def test_report_advances_cursor_per_thread(home, monkeypatch):
    from platforms import tos as tos_mod
    monkeypatch.setattr(tos_mod, "check_tos", lambda *a, **k: {"status": "ok"})
    a = _start(home)
    now = time.time()
    res = a.report(_msgs(
        ("c1", "m1", "them", "hey", now - 10),
        ("c2", "m1", "them", "hello there", now - 10),
        ("c2", "m2", "them", "are you around?", now - 5),
    ))
    assert res["ok"]
    assert dm_state.get_last_seen(home, "x", "main", "c1") == "m1"
    assert dm_state.get_last_seen(home, "x", "main", "c2") == "m2"


# ------------------------------------------------------- duplicate guard ---

def test_no_double_reply_to_same_message(home, monkeypatch):
    from platforms import tos as tos_mod
    monkeypatch.setattr(tos_mod, "check_tos", lambda *a, **k: {"status": "ok"})
    a = _start(home)
    now = time.time()
    m = _msgs(("c1", "m1", "them", "hey, quick question?", now - 10))
    r1 = a.report(m)
    queued1 = sum(len(t["replies_queued"]) for t in r1["threads"])
    assert queued1 == 1
    # Same observation again: nothing new, nothing queued.
    r2 = a.report(m)
    queued2 = sum(len(t["replies_queued"]) for t in r2["threads"])
    assert queued2 == 0
    assert all(t["new_inbound"] == 0 for t in r2["threads"])


def test_inbound_already_answered_in_thread_is_skipped(home, monkeypatch):
    from platforms import tos as tos_mod
    monkeypatch.setattr(tos_mod, "check_tos", lambda *a, **k: {"status": "ok"})
    a = _start(home)
    now = time.time()
    res = a.report(_msgs(
        ("c1", "m1", "them", "hi", now - 60),
        ("c1", "m2", "me", "hey! what's up?", now - 50),
    ))
    # m1 was already answered in-thread by m2: no draft.
    assert sum(len(t["replies_queued"]) for t in res["threads"]) == 0
    assert dm_state.get_last_seen(home, "x", "main", "c1") == "m2"


def test_messages_processed_oldest_first(home, monkeypatch):
    from platforms import tos as tos_mod
    monkeypatch.setattr(tos_mod, "check_tos", lambda *a, **k: {"status": "ok"})
    a = _start(home)
    now = time.time()
    res = a.report(_msgs(
        ("c1", "m2", "them", "second message here?", now - 5),
        ("c1", "m1", "them", "first message here?", now - 10),
    ))
    queued = res["threads"][0]["replies_queued"]
    assert [q["approval_id"] for q in queued]  # both queued
    items = aq.list_items(home, "pending")
    drafts = [i["payload"]["in_reply_to"] for i in items
              if i["type"] == "dm"]
    assert drafts == ["m1", "m2"], "oldest first"


# ------------------------------------------------------------ style gate ---

def test_style_gate_em_dash_split():
    out = style_mod.gate("Well — that's interesting news")
    assert "—" not in out
    assert out == "Well. That's interesting news"


def test_style_gate_spaced_en_dash():
    out = style_mod.gate("fast – and reliable")
    assert "–" not in out
    assert "fast, and reliable" == out


def test_style_gate_banned_phrases_removed():
    out = style_mod.gate("I hope this helps! Let me know.")
    assert "i hope this helps" not in out.lower()
    assert out == "Let me know."
    out2 = style_mod.gate("Certainly, I can do that for you.")
    assert "certainly" not in out2.lower()
    assert out2 == "I can do that for you."


def test_style_gate_long_sentence_split():
    long = ("This is a very long sentence that just keeps going and going "
            "and it never seems to stop at all, and it really should end")
    out = style_mod.gate(long)
    assert all(len(s.split()) <= 24 for s in out.split(". "))


def test_style_gate_never_silent():
    assert style_mod.gate("") == "Got it."
    assert style_mod.gate("Certainly. I hope this helps.") == "Got it."
    assert "—" not in style_mod.gate("a — b")


def test_style_gate_keeps_contractions():
    out = style_mod.gate("don't worry, it's fine and can't be better")
    assert "don't" in out and "it's" in out and "can't" in out


# --------------------------------------------------------------- replier ---

def test_replier_media_requests_get_honest_fallback(home):
    draft, info = replier_mod.draft_reply(
        home, "x", "main", "can you send me a voice note about sora?")
    assert info["intent"] == "voice_request"
    assert info["media_requested"] and info["fallback_used"]
    assert "can't send voice notes" in draft
    assert "—" not in draft

    draft, info = replier_mod.draft_reply(
        home, "x", "main", "send me a pic of your setup")
    assert info["intent"] == "image_request"
    assert "can't send pictures" in draft

    draft, info = replier_mod.draft_reply(
        home, "x", "main", "send me a video explaining it")
    assert info["intent"] == "video_request"
    assert "can't send videos" in draft


def test_replier_text_is_default_and_gated(home):
    draft, info = replier_mod.draft_reply(home, "x", "main", "hey")
    assert info["intent"] == "greeting"
    assert not info["media_requested"]
    assert "—" not in draft and "–" not in draft


def test_replier_credential_bait_is_high_risk(home):
    draft, info = replier_mod.draft_reply(
        home, "x", "main",
        "my account got locked, can you log in for me? password is hunter2")
    assert info["intent"] == "credential_bait"
    assert info["risk"] == "high"
    assert "hunter2" not in draft, "draft must not echo the secret"


# ------------------------------------------------------- stop conditions ---

def test_stop_deactivates_with_reason(home):
    a = _start(home)
    res = a.stop("operator paused")
    assert res["active"] is False
    st = a.status()
    assert st["active"] is False
    assert st["stop_reason"] == "operator paused"
    tick = a.tick()
    assert tick["ok"] is False and tick["skipped"] == "agent not active"


def test_idle_thread_parked_after_window(home, monkeypatch):
    from platforms import tos as tos_mod
    monkeypatch.setattr(tos_mod, "check_tos", lambda *a, **k: {"status": "ok"})
    a = DMAgent(home, "x", "main",
                config={"poll_interval": 600, "stop_after_idle_hours": 1})
    a.start()
    old = time.time() - 7200  # 2h ago, window is 1h
    dm_state.set_last_seen(home, "x", "main", "c-old", "m1",
                           last_inbound_id="m1", last_inbound_ts=old)
    res = a.tick(trigger="manual")
    assert res["ok"] is True
    assert "c-old" in res["parked_idle_threads"]
    row = dm_state.get_thread(home, "x", "main", "c-old")
    assert row["idle_parked"] == 1


# --------------------------------------------------- tiktok adapter ready ---

def test_tiktok_adapter_ready_with_web_readable_bodies():
    ok, reason = tiktok_adapter.readiness()
    assert ok is True
    assert "readable on web" in reason
    assert tiktok_adapter.STATUS == "ready"
    steps = tiktok_adapter.check_steps("main", [])
    assert isinstance(steps, list) and len(steps) >= 4
    assert any("tiktok.com/messages" in s for s in steps)
    assert any("isn't supported" in s for s in steps)  # placeholder honesty
    norm = tiktok_adapter.normalize({"threads": [
        {"thread_id": "dagreat00100", "messages": [
            {"id": "m1", "from": "them", "text": "How are you??", "ts": 1.0},
            {"id": "m2", "from": "me", "text": "doing well", "ts": 2.0},
        ]}]})
    assert [m["sender"] for m in norm] == ["them", "me"]
    assert norm[0]["thread_id"] == "dagreat00100"
    a = DMAgent("/tmp/nope", "tiktok", "main")
    res = a.tick()
    assert res.get("refused") is not True
    assert "app-only" not in str(res)


def test_registry_lists_four_platforms():
    assert set(SUPPORTED) == {"x", "tiktok", "instagram", "facebook", "threads"}
    for p in SUPPORTED:
        mod = get_adapter(p)
        assert mod.PLATFORM == p
        assert mod.STATUS in ("ready", "refused", "stub")


# ------------------------------------------------- tickets with receipts ---

def test_tick_issues_dm_check_ticket_with_receipts(home):
    a = _start(home)
    res = a.tick(trigger="manual")
    assert res["ok"] is True
    t = tickets_mod.get(home, res["ticket_id"])
    assert t["action"] == "dm_check"
    assert t["status"] == "issued"
    assert set(t["receipts"]) >= {"tos", "approval", "rate_limit"}
    assert t["receipts"]["tos"]["class"] == "automated_reading"
    assert any("STOP" in s or "Login check" in s for s in t["steps"])
    assert "dm_check" in steps_mod.supported_actions()


def test_report_fulfills_dm_check_ticket(home, monkeypatch):
    from platforms import tos as tos_mod
    monkeypatch.setattr(tos_mod, "check_tos", lambda *a, **k: {"status": "ok"})
    a = _start(home)
    tick = a.tick(trigger="manual")
    tid = tick["ticket_id"]
    now = time.time()
    res = a.report(_msgs(("c1", "m1", "them", "hello?", now - 5)))
    assert res["ticket_fulfilled"] == tid
    t = tickets_mod.get(home, tid)
    assert t["status"] == "fulfilled"
    assert "m1" in t["fulfillment"]["evidence"]


def test_approval_of_dm_item_issues_dm_send_ticket(home, monkeypatch):
    from platforms import tos as tos_mod
    monkeypatch.setattr(tos_mod, "check_tos", lambda *a, **k: {"status": "ok"})
    a = _start(home)
    now = time.time()
    res = a.report(_msgs(("c1", "m1", "them", "hey, how does sora work?", now - 5)))
    qid = res["threads"][0]["replies_queued"][0]["approval_id"]
    item = aq.approve(home, qid, decided_by="user")
    t = tickets_mod.get(home, item["ticket_id"])
    assert t["action"] == "dm_send"
    assert t["status"] == "issued"
    assert set(t["receipts"]) >= {"tos", "approval", "rate_limit"}
    assert t["parameters"]["draft"]
    assert "—" not in t["parameters"]["draft"]


def test_dm_send_refused_at_ticket_issuance_on_x(home):
    # Real ToS layer, no monkeypatch: X automated_dms is prohibited.
    # Drafting is proposing (allowed); the SEND is what the pipeline
    # refuses — at ticket issuance, not at draft time.
    from platforms.tos import ToSRefusal
    a = _start(home)
    now = time.time()
    res = a.report(_msgs(("c1", "m1", "them", "hey there", now - 5)))
    t = res["threads"][0]
    assert t["refused"] == []
    assert len(t["replies_queued"]) == 1
    qid = t["replies_queued"][0]["approval_id"]
    # cursor still advances: seen means seen
    assert dm_state.get_last_seen(home, "x", "main", "c1") == "m1"
    # approving must NOT issue a dm_send ticket on X: prohibited.
    with pytest.raises(ToSRefusal):
        aq.approve(home, qid, decided_by="user")
    item = aq.get(home, qid)
    assert item["status"] == "pending"
    assert "ticket_id" not in item
    assert tickets_mod.list_tickets(home, status="issued") == []


def test_dedup_falls_back_to_timestamps_when_cursor_unknown(home):
    # Live incident 2026-09-25: the stored cursor was a synthetic UUID
    # never present in observations, so every old inbound message was
    # treated as new. The fallback compares against last_inbound_at.
    a = _start(home)
    now = time.time()
    dm_state.set_last_seen(home, "x", "main", "c1", "uuid-poison",
                           last_inbound_id="m_old",
                           last_inbound_ts=now - 100)
    res = a.report(_msgs(
        ("c1", "m_old", "them", "old message", now - 200),
        ("c1", "m_new", "them", "new message", now - 5)))
    t = res["threads"][0]
    assert len(t["replies_queued"]) == 1
    item = aq.get(home, t["replies_queued"][0]["approval_id"])
    assert item["payload"]["in_reply_to"] == "m_new"


# -------------------------------------- thread-id normalization ---

def _seed_legacy_row(home, platform, account, thread_id, last_seen_id="",
                     last_inbound_id="", last_inbound_at=0.0):
    """Insert a raw dm_agent_state row, bypassing normalization — simulates
    state written before canonicalization (suffixed display ids)."""
    from core import memory as mem_mod
    mem_mod.init_db(home)
    cx = mem_mod.connect(home)
    try:
        cx.execute(
            "INSERT OR REPLACE INTO dm_agent_state "
            "(platform, account_label, thread_id, last_seen_id, "
            "last_inbound_id, last_inbound_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (platform, account, thread_id, last_seen_id, last_inbound_id,
             float(last_inbound_at), mem_mod.utcnow()))
        cx.commit()
    finally:
        cx.close()


def test_canonical_thread_id_strips_display_suffix():
    bare = "1920160303695716352-2100845624027418624"
    assert dm_state.canonical_thread_id(bare) == bare
    assert dm_state.canonical_thread_id(
        bare + " (Zenas Ayansipe @dagreat00100)") == bare
    assert dm_state.canonical_thread_id("__agent__") == "__agent__"
    # idempotent: canonicalizing twice is stable
    once = dm_state.canonical_thread_id(
        bare + " (Zenas Instinct @Instinct_zen)")
    assert dm_state.canonical_thread_id(once) == once == bare


def test_sweep_removes_bare_display_name_alias_rows(home):
    """Regression: bare display-name alias rows (legacy junk with no numeric
    id, e.g. "Zenas Ayansipe @dagreat00100") must be swept away while the
    canonical thread row keeps its cursor. Live incident 2026-09-25: a stale
    alias cursor caused 6 phantom reply drafts for already-handled DMs."""
    bare = "1920160303695716352-2100845624027418624"
    alias = "Zenas Ayansipe @dagreat00100"
    _seed_legacy_row(home, "x", "main", bare, last_seen_id="m42",
                     last_inbound_id="m42", last_inbound_at=100.0)
    _seed_legacy_row(home, "x", "main", alias, last_seen_id="sep25-0702",
                     last_inbound_id="m1", last_inbound_at=50.0)
    assert dm_state._sweep_variants(home, "x", "main") is True
    tids = [t["thread_id"] for t in dm_state.list_threads(home, "x", "main")]
    assert alias not in tids
    assert bare in tids
    assert dm_state.get_last_seen(home, "x", "main", bare) == "m42"
    # second sweep is a no-op
    assert dm_state._sweep_variants(home, "x", "main") is False


def test_sweep_keeps_alias_rows_when_no_canonical_thread(home):
    """The alias sweep must never wipe the whole thread list: with no
    canonical row present, alias rows are left alone."""
    _seed_legacy_row(home, "x", "main", "Zenas Ayansipe @dagreat00100",
                     last_seen_id="m1")
    assert dm_state._sweep_variants(home, "x", "main") is False
    tids = [t["thread_id"] for t in dm_state.list_threads(home, "x", "main")]
    assert "Zenas Ayansipe @dagreat00100" in tids


def test_bare_and_suffixed_ids_resolve_to_one_row(home):
    suffixed = ("1920160303695716352-2100845624027418624 "
                "(Zenas Ayansipe @dagreat00100)")
    dm_state.set_last_seen(home, "x", "main", suffixed, "m1",
                           last_inbound_id="m1", last_inbound_ts=100.0)
    # the bare form (what browser reads return now) sees the same row
    assert dm_state.get_last_seen(
        home, "x", "main", "1920160303695716352-2100845624027418624") == "m1"
    rows = dm_state.list_threads(home, "x", "main")
    assert [r["thread_id"] for r in rows] == \
        ["1920160303695716352-2100845624027418624"]


def test_merge_keeps_latest_cursor_and_max_inbound(home):
    bare = "2100622701643657216-2100845624027418624"
    suffixed = bare + " (Zenas Instinct @Instinct_zen)"
    # legacy suffixed row holds the older cursor; a bare row exists with
    # the newer cursor — the merge keeps the newest, deletes the variant
    _seed_legacy_row(home, "x", "main", suffixed, last_seen_id="m_old",
                     last_inbound_id="m_old", last_inbound_at=100.0)
    _seed_legacy_row(home, "x", "main", bare, last_seen_id="m_new",
                     last_inbound_id="m_new", last_inbound_at=200.0)
    row = dm_state.get_thread(home, "x", "main", bare)
    assert row["last_seen_id"] == "m_new"
    assert row["last_inbound_id"] == "m_new"
    assert row["last_inbound_at"] == 200.0
    rows = dm_state.list_threads(home, "x", "main")
    assert [r["thread_id"] for r in rows] == [bare]
    # second sweep is a no-op: nothing left to merge
    assert dm_state.list_threads(home, "x", "main") == rows


def test_merge_adopts_freshest_variant_cursor(home):
    bare = "1920160303695716352-2100845624027418624"
    suffixed = bare + " (Zenas Ayansipe @dagreat00100)"
    # only the legacy suffixed row exists: the bare lookup must adopt its
    # cursor, not start blank (a blank cursor is what caused the spurious
    # first-sight drafts in the 2026-09-25 live incident)
    _seed_legacy_row(home, "x", "main", suffixed, last_seen_id="m9",
                     last_inbound_id="m9", last_inbound_at=300.0)
    assert dm_state.get_last_seen(home, "x", "main", bare) == "m9"
    row = dm_state.get_thread(home, "x", "main", bare)
    assert row["last_inbound_at"] == 300.0
    assert [r["thread_id"] for r in
            dm_state.list_threads(home, "x", "main")] == [bare]


def test_mixed_format_report_no_duplicates_no_spurious_drafts(home,
                                                             monkeypatch):
    # Live incident 2026-09-25: legacy state keyed by suffixed ids, browser
    # reads return bare ids. report() must resolve to the one merged row
    # and NOT treat already-seen messages as new.
    from platforms import tos as tos_mod
    monkeypatch.setattr(tos_mod, "check_tos", lambda *a, **k: {"status": "ok"})
    a = _start(home)
    now = time.time()
    bare = "1920160303695716352-2100845624027418624"
    suffixed = bare + " (Zenas Ayansipe @dagreat00100)"
    # legacy state: everything through m2 already seen
    _seed_legacy_row(home, "x", "main", suffixed, last_seen_id="m2",
                     last_inbound_id="m2", last_inbound_at=now - 50)
    # browser read returns the BARE id with the same already-seen messages
    res = a.report(_msgs(
        (bare, "m1", "them", "hello", now - 100),
        (bare, "m2", "them", "are you there", now - 50)))
    t = res["threads"][0]
    assert t["thread_id"] == bare
    assert t["new_inbound"] == 0
    assert t["replies_queued"] == []
    assert t["rate_limited"] == []
    # one row, canonical id, cursor intact — no duplicate bare-id row
    rows = dm_state.list_threads(home, "x", "main")
    assert [r["thread_id"] for r in rows] == [bare]
    assert dm_state.get_last_seen(home, "x", "main", bare) == "m2"


def test_new_inbound_after_merge_still_queues(home, monkeypatch):
    # The merge must not swallow genuinely new messages: m1 seen under the
    # legacy suffixed id, m2 arrives on the bare id -> exactly one draft.
    from platforms import tos as tos_mod
    monkeypatch.setattr(tos_mod, "check_tos", lambda *a, **k: {"status": "ok"})
    a = _start(home)
    now = time.time()
    bare = "2100622701643657216-2100845624027418624"
    suffixed = bare + " (Zenas Instinct @Instinct_zen)"
    _seed_legacy_row(home, "x", "main", suffixed, last_seen_id="m1",
                     last_inbound_id="m1", last_inbound_at=now - 100)
    res = a.report(_msgs(
        (bare, "m1", "them", "old one", now - 100),
        (bare, "m2", "them", "new question here", now - 5)))
    t = res["threads"][0]
    assert t["new_inbound"] == 1
    assert len(t["replies_queued"]) == 1
    assert dm_state.get_last_seen(home, "x", "main", bare) == "m2"
    assert [r["thread_id"] for r in
            dm_state.list_threads(home, "x", "main")] == [bare]


# ------------------------------------------------- cadence / pile-up ---

def test_poll_interval_floor_enforced():
    a = DMAgent("/tmp/nope", "x", "main", config={"poll_interval": 10})
    assert a.poll_interval == POLL_INTERVAL_MIN
    b = DMAgent("/tmp/nope", "x", "main", config={})
    assert b.poll_interval == POLL_INTERVAL_DEFAULT
    assert TARGET_INTERVAL_ASPIRATION == 35


def test_tick_skips_before_interval_without_trigger(home):
    a = _start(home)
    res = a.tick()
    assert res["ok"] is False
    assert res["skipped"] == "poll interval not elapsed"
    assert res["next_in_s"] > 0


def test_trigger_jumps_queue_but_not_pileup(home):
    a = _start(home)
    r1 = a.tick(trigger="gmail-notification")
    assert r1["ok"] is True
    assert r1["trigger"] == "gmail-notification"
    r2 = a.tick(trigger="manual")
    assert r2["ok"] is False
    assert r2["skipped"] == "previous check in flight"
    assert r2["pending_ticket"] == r1["ticket_id"]


def test_no_pileup_after_fulfill(home):
    a = _start(home)
    r1 = a.tick(trigger="manual")
    now = time.time()
    a.report(_msgs(("c1", "m1", "them", "hi", now - 5)))
    # ticket fulfilled by report -> next triggered tick may proceed
    r2 = a.tick(trigger="manual")
    assert r2["ok"] is True
    assert r2["ticket_id"] != r1["ticket_id"]


# ------------------------------------------------- credential tripwire ---

def test_no_credentials_in_dm_agents():
    """No password/token/secret/key material in dm_agents code or state."""
    import re
    root = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "dm_agents")
    pat = re.compile(
        r"password\s*=\s*['\"][^'\"]+['\"]|"
        r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]|"
        r"token\s*=\s*['\"][^'\"]{8,}['\"]", re.I)
    hits = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d != "__pycache__"]
        for f in fn:
            if not f.endswith(".py"):
                continue
            text = open(os.path.join(dp, f), encoding="utf-8").read()
            for m in pat.finditer(text):
                # allow the words in comments/docstrings about the rule
                hits.append((f, m.group(0)[:40]))
    assert not hits, f"credential-like assignment in dm_agents: {hits}"


def test_dm_check_ticket_carries_no_credentials(home):
    """dm_check tickets carry instructions + thread ids only — no credential
    fields and no credential values. (The login-wall step legitimately
    *prohibits* typing passwords; that prohibition is not a credential.)"""
    a = _start(home)
    res = a.tick(trigger="manual")
    t = tickets_mod.get(home, res["ticket_id"])
    params = t.get("parameters") or {}
    for key in params:
        assert key.lower() not in (
            "password", "passcode", "token", "secret", "api_key"), key
    blob = json.dumps(t)
    assert not re.search(
        r"(password|passcode|api[_-]?key)\s*[:=]\s*['\"][^'\"]+['\"]",
        blob, re.I), "credential-like value in dm_check ticket"


def test_report_never_reproposes_decided_messages(home, monkeypatch):
    # Regression 2026-09-25: the loop re-queued the same drafts every cycle
    # after the operator rejected them, because the duplicate guard only
    # looked at pending items. A decided message (rejected/approved/done)
    # must never be re-proposed.
    from platforms import tos as tos_mod
    monkeypatch.setattr(tos_mod, "check_tos", lambda *a, **k: {"status": "ok"})
    a = _start(home)
    tid = "conv-decided"
    now = time.time()
    i1 = aq.propose(home, "dm", "x", "main", summary="r",
                    payload={"thread_id": tid, "in_reply_to": "m1"},
                    reason="t", risk="normal")
    aq.reject(home, i1["id"], reason="operator said no", decided_by="user")
    aq.propose(home, "dm", "x", "main", summary="r",
               payload={"thread_id": tid, "in_reply_to": "m2"},
               reason="t", risk="normal")  # left pending
    i4 = aq.propose(home, "dm", "x", "main", summary="r",
                    payload={"thread_id": tid, "in_reply_to": "m4"},
                    reason="t", risk="normal")
    aq.set_status(home, i4["id"], "done")
    res = a.report(_msgs(
        (tid, "m0", "me", "hi", now - 300),
        (tid, "m1", "them", "old q", now - 200),
        (tid, "m2", "them", "old q2", now - 100),
        (tid, "m4", "them", "handled already", now - 50),
        (tid, "m3", "them", "brand new", now - 10)))
    t = res["threads"][0]
    # m1 rejected-skipped, m2 pending-skipped, m4 done-skipped: only m3 queues.
    assert len(t["replies_queued"]) == 1
    item = aq.get(home, t["replies_queued"][0]["approval_id"])
    assert item is not None
    assert item["payload"]["in_reply_to"] == "m3"
