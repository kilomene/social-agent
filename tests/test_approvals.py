"""Unified approval queue tests: propose/approve/reject, per-type policy, audit."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from approvals import queue as q
from conftest import add_account, cli, state, write_policy


def _propose_via_engage(home):
    r = cli("engage", "like", "--platform", "tiktok", "--account", "main",
            "--target", "v9", home=home)
    assert r.returncode == 0, r.stderr
    items = state(home, "approvals/pending.json")
    assert len(items) == 1
    return items[0]


def test_propose_creates_pending_queue_item(home):
    add_account(home)
    item = _propose_via_engage(home)
    assert item["status"] == "pending"
    assert item["type"] == "like"
    assert item["ref"]["store"] == "actions.json"
    actions = state(home, "actions.json")
    assert actions[0]["status"] == "proposed"


def test_approve_executes_underlying_action(home):
    add_account(home)
    item = _propose_via_engage(home)
    r = cli("approvals", "approve", "--id", item["id"], home=home)
    assert r.returncode == 0, r.stderr
    assert "approved" in r.stdout.lower()
    assert state(home, "actions.json")[0]["status"] == "approved"
    items = state(home, "approvals/pending.json")
    assert items[0]["status"] == "approved"
    assert items[0]["decided_by"] == "user"


def test_reject_logs_reason(home):
    add_account(home)
    item = _propose_via_engage(home)
    r = cli("approvals", "reject", "--id", item["id"],
            "--reason", "looks spammy", home=home)
    assert r.returncode == 0, r.stderr
    assert state(home, "actions.json")[0]["status"] == "rejected"
    items = state(home, "approvals/pending.json")
    assert items[0]["status"] == "rejected"
    assert items[0]["decision_reason"] == "looks spammy"


def test_approve_unknown_id_refused(home):
    add_account(home)
    r = cli("approvals", "approve", "--id", "q-nope", home=home)
    assert r.returncode != 0


def test_per_type_auto_policy(tmp_path, home):
    pol = write_policy(str(tmp_path / "policy.yaml"),
                       approvals={"per_type": {"like": "auto"}})
    add_account(home)
    r = cli("engage", "like", "--platform", "tiktok", "--account", "main",
            "--target", "v9", home=home, policy=pol)
    assert r.returncode == 0, r.stderr
    assert "AUTO-APPROVED" in r.stdout
    items = state(home, "approvals/pending.json")
    assert items[0]["status"] == "approved"
    assert "auto" in items[0]["reason"]


def test_per_type_policy_defaults_require():
    assert q.per_type_policy({}, "like") == "require"
    assert q.per_type_policy({"approvals": {}}, "weird") == "require"


def test_approve_twice_refused(home):
    add_account(home)
    item = _propose_via_engage(home)
    assert cli("approvals", "approve", "--id", item["id"], home=home).returncode == 0
    r = cli("approvals", "approve", "--id", item["id"], home=home)
    assert r.returncode != 0
