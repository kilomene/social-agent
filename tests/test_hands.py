"""Execution ticket tests (brain -> hands).

The repo never drives a browser: approving a proposal issues a
machine-readable execution ticket (hands/tickets.py); an external agent
(hands.backend.HandsBackend — mocked here) claims it, fulfills it
visibly in its own browser, and the operator confirms via the existing
engage done / approval flow. Tickets are idempotent — a ticket can never
be fulfilled twice.

Also covers the credential tripwire: no credential-like fields
(password/token/secret/key) may appear in the ticket schema or in stored
ticket JSON. Logins live in the agent's secure vault (or the user's own
browser) — never in the repo or its state.
"""

import json
import os
import re

import pytest

from hands import tickets
from hands import steps as steps_mod
from hands.backend import HandsBackend, MockHandsBackend
from approvals import queue as aq
from conftest import add_account


# ------------------------------------------------------------ lifecycle ---

def _issue(home):
    return tickets.issue(
        home, "like", "tiktok", "main",
        parameters={"target_url": "https://www.tiktok.com/@x/video/1"},
        receipts={"tos": {"risk": "low", "checked": "test"}},
        source={"approval_id": "a-1"})


def test_issue_creates_machine_readable_ticket(home):
    t = _issue(home)
    assert t["status"] == "issued"
    assert t["action"] == "like"
    assert t["platform"] == "tiktok"
    assert t["account"] == "main"
    assert t["target"] == "https://www.tiktok.com/@x/video/1"
    assert t["idem_key"].startswith("ticket:")
    assert t["receipts"]["tos"]["risk"] == "low"
    assert len(t["steps"]) >= 3
    assert any("STOP" in s for s in t["steps"]), \
        "steps must include the login-wall rule"
    # stored on disk as JSON
    stored = tickets.get(home, t["id"])
    assert stored["id"] == t["id"]
    assert os.path.exists(os.path.join(home, "tickets.json"))


def test_claim_fulfill_lifecycle(home):
    t = _issue(home)
    tickets.claim(home, t["id"], host_agent="muse", session_id="sess-1")
    got = tickets.get(home, t["id"])
    assert got["status"] == "claimed"
    assert got["host"]["agent"] == "muse"
    assert got["host"]["session_id"] == "sess-1"
    tickets.fulfill(home, t["id"], evidence="liked, heart filled",
                    host_session_id="sess-1")
    got = tickets.get(home, t["id"])
    assert got["status"] == "fulfilled"
    assert got["fulfillment"]["evidence"] == "liked, heart filled"
    # host session registry records the fulfillment
    sessions = tickets.list_host_sessions(home)
    assert "sess-1" in sessions
    assert t["id"] in sessions["sess-1"]["tickets_fulfilled"]


def test_invalid_transitions_rejected(home):
    t = _issue(home)
    with pytest.raises(ValueError):
        tickets.fulfill(home, t["id"], "x")   # issued, not claimed
    with pytest.raises(KeyError):
        tickets.claim(home, "tkt-nope", "muse", "s1")
    tickets.claim(home, t["id"], "muse", "s1")
    with pytest.raises(ValueError):
        tickets.cancel(home, t["id"])          # claimed: cannot cancel


def test_cancel_and_fail(home):
    t = _issue(home)
    tickets.cancel(home, t["id"], reason="changed mind")
    assert tickets.get(home, t["id"])["status"] == "cancelled"
    with pytest.raises(ValueError):
        tickets.claim(home, t["id"], "muse", "s1")  # cancelled: no claim
    q = _issue(home)
    tickets.claim(home, q["id"], "muse", "s1")
    tickets.fail(home, q["id"], error="login wall hit")
    assert tickets.get(home, q["id"])["status"] == "failed"


def test_claim_twice_rejected(home):
    t = _issue(home)
    tickets.claim(home, t["id"], "muse", "s1")
    with pytest.raises(ValueError):
        tickets.claim(home, t["id"], "muse", "s2")   # already claimed


def test_fulfill_twice_rejected_idempotent(home):
    """A ticket can NEVER be fulfilled twice — the never-repeat guarantee."""
    t = _issue(home)
    tickets.claim(home, t["id"], "muse", "s1")
    tickets.fulfill(home, t["id"], "did it", host_session_id="s1")
    with pytest.raises(ValueError):
        tickets.fulfill(home, t["id"], "did it again", host_session_id="s1")
    # exactly one completed journal entry for the fulfill transition
    from core import resume_engine as rec
    dones = [e for e in rec._read_entries(home)
             if e.get("action_type") == "ticket-done"
             and e.get("target") == t["id"]
             and e.get("status") == "completed"]
    assert len(dones) == 1


def test_fulfill_requires_evidence(home):
    t = _issue(home)
    tickets.claim(home, t["id"], "muse", "s1")
    with pytest.raises(ValueError):
        tickets.fulfill(home, t["id"], evidence="   ")


def test_claim_requires_agent_and_session(home):
    t = _issue(home)
    with pytest.raises(ValueError):
        tickets.claim(home, t["id"], "", "")


def test_unknown_action_rejected(home):
    with pytest.raises(ValueError):
        tickets.issue(home, "hack_the_planet", "x", "main")


def test_step_templates_cover_all_actions(home):
    for action in steps_mod.supported_actions():
        st = steps_mod.build_steps(action, "x", {})
        assert len(st) >= 3
        assert any("STOP" in s for s in st), \
            f"{action} steps missing login-wall rule"


# ------------------------------------------------- approval issues ticket ---

def test_approval_issues_ticket_with_receipts(home):
    add_account(home)
    item = aq.propose(home, "like", "tiktok", "main",
                      summary="like an interesting post",
                      payload={"target_url": "https://x.example/p/1"},
                      risk="low")
    item = aq.approve(home, item["id"], decided_by="user")
    assert item.get("ticket_id"), "approving must issue an execution ticket"
    t = tickets.get(home, item["ticket_id"])
    assert t is not None
    assert t["status"] == "issued"
    assert t["action"] == "like"
    assert t["target"] == "https://x.example/p/1"
    assert t["source"]["approval_id"] == item["id"]
    # the ToS / approval / rate-limit receipts prove the guard order ran
    for receipt in ("tos", "approval", "rate_limit"):
        assert receipt in t["receipts"], f"missing {receipt} receipt"
    assert t["receipts"]["approval"]["approval_id"] == item["id"]
    assert t["receipts"]["approval"]["decided_by"] == "user"
    assert len(t["steps"]) >= 3


# ------------------------------------------------------- mock hands backend ---

def test_mock_hands_backend_fulfills_ticket(home):
    add_account(home)
    item = aq.propose(home, "comment", "tiktok", "main",
                      summary="reply to a question",
                      payload={"target_url": "https://x.example/p/2",
                               "text": "great point!"},
                      risk="low")
    item = aq.approve(home, item["id"], decided_by="user")
    backend = MockHandsBackend()
    assert isinstance(backend, HandsBackend)
    t = tickets.get(home, item["ticket_id"])
    tickets.claim(home, t["id"], host_agent="muse", session_id="live-1")
    evidence = backend.fulfill(tickets.get(home, t["id"]))
    assert evidence, "backend must return evidence"
    tickets.fulfill(home, t["id"], evidence, host_session_id="live-1")
    assert tickets.get(home, t["id"])["status"] == "fulfilled"
    assert backend.fulfilled == [t["id"]]
    # operator confirms via the existing flow — ticket stays fulfilled once
    with pytest.raises(ValueError):
        tickets.fulfill(home, t["id"], evidence, host_session_id="live-1")


def test_base_backend_refuses_unimplemented():
    with pytest.raises(NotImplementedError):
        HandsBackend().fulfill({"id": "tkt-x"})


# ------------------------------------------------------- credential rule ---

CREDENTIAL_WORDS = re.compile(
    r"(password|passwd|pwd|secret|credential|api[-_ ]?key|apikey|"
    r"private[-_ ]?key|access[-_ ]?token|auth[-_ ]?token|bearer|"
    r"client[-_ ]?secret|session[-_ ]?token|cookie)",
    re.IGNORECASE)


def _credentialish_names(obj):
    """All dict key names in a nested structure."""
    names = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                names.append(str(k))
                walk(v)
        elif isinstance(o, (list, tuple)):
            for v in o:
                walk(v)
    walk(obj)
    return names


def test_no_credential_fields_in_ticket_schema():
    for name in tickets.TICKET_SCHEMA:
        assert not CREDENTIAL_WORDS.search(name), \
            f"credential-like field in ticket schema: {name!r}"


def test_no_credential_fields_in_stored_tickets(home):
    t = _issue(home)
    tickets.claim(home, t["id"], "muse", "sess-1")
    tickets.fulfill(home, t["id"], "liked it", host_session_id="sess-1")
    path = os.path.join(home, "tickets.json")
    with open(path, encoding="utf-8") as fh:
        stored = json.load(fh)
    for name in _credentialish_names(stored):
        assert not CREDENTIAL_WORDS.search(name), \
            f"credential-like field in stored ticket JSON: {name!r}"
    # and no credential-looking VALUES smuggled into parameters either
    blob = json.dumps(stored)
    for word in ("password=", "passwd=", "api_key=", "client_secret="):
        assert word not in blob.lower()


def test_no_credential_fields_in_host_sessions(home):
    tickets.register_host_session(home, "muse", "sess-9",
                                  account_label="main", note="live session")
    tickets.record_ticket_session(home, "sess-9", "tkt-abc", "evidence text")
    sessions = tickets.list_host_sessions(home)
    for name in _credentialish_names(sessions):
        assert not CREDENTIAL_WORDS.search(name), \
            f"credential-like field in host sessions: {name!r}"


def _approval_item(itype="like", target="f1"):
    return {"id": "q-test", "type": itype, "platform": "facebook",
            "account": "main", "risk": "low", "summary": "test proposal",
            "payload": {"target": target}}


def test_issue_from_approval_refuses_fixture_target(home):
    """Regression: a targeted action whose target is a synthetic watcher-
    fixture id (no URL) must not mint a hands ticket — live 2026-09-25,
    tkt-acbc13 was issued for fixture target 'f1' and unfulfillable."""
    with pytest.raises(ValueError, match="not a resolvable URL"):
        tickets.issue_from_approval(home, _approval_item("like", "f1"))


def test_issue_from_approval_accepts_real_url_target(home):
    t = tickets.issue_from_approval(
        home, _approval_item("like", "https://www.facebook.com/post/123"))
    assert t["status"] == "issued"
    assert t["target"] == "https://www.facebook.com/post/123"


def test_issue_from_approval_post_needs_no_target(home):
    item = {"id": "q-test2", "type": "post", "platform": "facebook",
            "account": "main", "risk": "low", "summary": "test post",
            "payload": {"text": "hello world"}}
    t = tickets.issue_from_approval(home, item)
    assert t["status"] == "issued" and t["action"] == "post_text"
