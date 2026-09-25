"""Crisis mode tests: global pause, hold/re-pend, explicit resume only."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crisis import mode as cm
from conftest import add_account, cli, state


def _pending_item(home):
    return state(home, "approvals/pending.json")[0]


def test_crisis_blocks_acting_but_not_watchers(home):
    add_account(home)
    assert cli("crisis", "on", "--reason", "test spike", home=home).returncode == 0
    r = cli("engage", "follow", "--platform", "tiktok", "--account", "main",
            "--target", "someone", home=home)
    assert r.returncode == 2
    assert "crisis" in r.stderr.lower()
    # read-only monitoring still works
    r = cli("approvals", "list", home=home)
    assert r.returncode == 0
    r = cli("crisis", "status", home=home)
    assert r.returncode == 0 and "ACTIVE" in r.stdout


def test_crisis_holds_pending_and_repends_on_off(home):
    add_account(home)
    cli("engage", "follow", "--platform", "tiktok", "--account", "main",
        "--target", "someone", home=home)
    qid = _pending_item(home)["id"]
    cli("crisis", "on", home=home)
    assert _pending_item(home)["status"] == "held"
    r = cli("crisis", "off", home=home)
    assert r.returncode == 0
    assert _pending_item(home)["status"] == "pending"
    # held items need explicit re-approval; acting works again
    r = cli("engage", "follow", "--platform", "tiktok", "--account", "main",
            "--target", "other", home=home)
    assert r.returncode == 0
    # the re-pended item is NOT auto-approved: still needs a human decision
    r = cli("approvals", "approve", "--id", qid, home=home)
    assert r.returncode == 0
    assert _pending_item(home)["status"] == "approved"


def test_crisis_off_when_not_active(home):
    r = cli("crisis", "off", home=home)
    assert r.returncode == 0 and "already off" in r.stdout.lower()


def test_crisis_never_auto_resumes(tmp_path):
    import pytest
    home = str(tmp_path / "home")
    cm.activate(home, "x")
    assert cm.is_active(home)
    with pytest.raises(cm.CrisisActive):
        cm.check(home)
    # only an explicit deactivate clears it — nothing auto-resumes
    assert cm.is_active(home)
    cm.deactivate(home)
    assert not cm.is_active(home)
    cm.check(home)  # no raise when off


def test_crisis_state_shape(tmp_path):
    home = str(tmp_path / "home")
    st = cm.activate(home, "reason here", hold_fn=lambda: ["q-1"])
    assert st["active"] is True
    assert st["held"] == ["q-1"]
    assert st["reason"] == "reason here"
    assert "started_at" in st
