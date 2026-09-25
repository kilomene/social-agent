"""Tests for the per-platform Terms of Service compliance layer."""

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from platforms import tos  # noqa: E402
from conftest import cli, add_account  # noqa: E402


def test_all_platforms_have_valid_rules():
    for p in ["tiktok", "x", "instagram", "facebook", "youtube", "reddit",
              "threads"]:
        rules = tos.load_rules(p)
        assert rules["platform"] == p
        assert rules["last_checked"], f"{p} missing last_checked"
        assert set(rules["actions"]) == set(tos.ACTION_CLASSES), p
        for cls, rule in rules["actions"].items():
            assert rule["status"] in tos.STATUSES, (p, cls)
            assert rule.get("basis"), (p, cls)
            assert rule.get("sources"), (p, cls)


def test_prohibited_raises():
    with pytest.raises(tos.ToSRefusal) as ei:
        tos.check_tos("x", "automated_likes")
    assert "x.com/en/tos" in str(ei.value)


def test_restricted_returns_rule_with_advisory(capsys):
    rule = tos.check_tos("tiktok", "automated_likes")
    assert rule["status"] == "restricted"
    out = capsys.readouterr()
    assert "ToS note" in out.err and "tiktok/automated_likes" in out.err


def test_missing_platform_fails_closed():
    with pytest.raises(tos.ToSRefusal):
        tos.check_tos("myspace", "automated_likes")


def test_unknown_action_class_fails_closed():
    with pytest.raises(tos.ToSRefusal):
        tos.check_tos("tiktok", "automated_time_travel")


def test_cli_op_mapping_covers_engage_ops():
    for op in ["like", "comment", "follow", "retweet", "post", "profile", "watch"]:
        assert op in tos.CLI_OP_TO_CLASS, op


def _policy_without_ack_risk(tmp_path):
    """Repo policy.yaml with the tos.acknowledged_risk opt-in stripped.

    The live repo policy opts x in (owner's explicit 2026-09-25 choice);
    tests of the fail-closed default need a policy without it."""
    src = os.path.join(REPO, "policy", "policy.yaml")
    text = open(src, encoding="utf-8").read().replace("    - x\n", "")
    p = tmp_path / "policy-noack.yaml"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_cli_refuses_prohibited_action(home, tmp_path):
    add_account(home, platform="x", username="xt", label="main")
    r = cli("engage", "like", "--platform", "x", "--account", "main",
            "--target", "v1", home=home,
            policy=_policy_without_ack_risk(tmp_path))
    assert r.returncode == 2
    assert "ToS" in r.stderr


def test_cli_acknowledged_risk_downgrades_prohibited_to_restricted(home):
    # The repo's live policy.yaml opts x into tos.acknowledged_risk
    # (owner's explicit 2026-09-25 opt-in): the prohibition downgrades to
    # restricted with a loud logged advisory instead of refusing.
    add_account(home, platform="x", username="xt", label="main")
    r = cli("engage", "like", "--platform", "x", "--account", "main",
            "--target", "v1", home=home)
    assert r.returncode == 0
    assert "ACKNOWLEDGED-RISK ADVISORY" in r.stderr
    assert "DRY-RUN proposal" in r.stdout


def test_cli_refuses_prohibited_watcher(home):
    add_account(home, platform="x", username="xt", label="main")
    r = cli("watch", "start", "--type", "notification", "--platform", "x",
            "--account", "main", "--id", "wx", home=home)
    assert r.returncode == 2
    assert "ToS" in r.stderr


def test_cli_restricted_action_proceeds_with_note(home):
    add_account(home, platform="tiktok", username="tt", label="main")
    r = cli("engage", "like", "--platform", "tiktok", "--account", "main",
            "--target", "v1", home=home)
    assert r.returncode == 0
    assert "ToS note" in r.stderr
    assert "DRY-RUN proposal" in r.stdout


def test_doctor_reports_tos_rules(home):
    r = cli("doctor", home=home)
    assert r.returncode == 0
    assert "ToS rules parse" in r.stdout
