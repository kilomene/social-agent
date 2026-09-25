"""Policy enforcement tests: yaml parsing, rate limits, quiet hours, approvals."""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy import yaml_lite
from conftest import add_account, cli, state, write_policy

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_POLICY = os.path.join(REPO, "policy", "policy.yaml")


def test_yaml_lite_parses_real_policy():
    p = yaml_lite.load(REAL_POLICY)
    assert p["version"] == 1
    assert p["defaults"]["dry_run"] is True
    assert p["rate_limits"]["x"]["actions_per_day"] == 100
    assert "comment_spam" in p["prohibited"]
    assert isinstance(p["approvals"]["required_for"], list)


def test_yaml_lite_rejects_bad_input():
    with pytest.raises(yaml_lite.YamlLiteError):
        yaml_lite.loads("a:\n\tb: 1\n")  # tabs
    with pytest.raises(yaml_lite.YamlLiteError):
        yaml_lite.loads("a:\n   b: 1\n")  # 3-space indent
    with pytest.raises(yaml_lite.YamlLiteError):
        yaml_lite.loads("just a string\n")


def test_rate_limit_enforced(tmp_path, home):
    pol = write_policy(str(tmp_path / "policy.yaml"),
                       rate_limits={"tiktok": {"actions_per_hour": 1,
                                              "actions_per_day": 1}})
    add_account(home)
    r1 = cli("engage", "like", "--platform", "tiktok", "--account", "main",
             "--target", "v1", home=home, policy=pol)
    assert r1.returncode == 0
    r2 = cli("engage", "like", "--platform", "tiktok", "--account", "main",
             "--target", "v2", home=home, policy=pol)
    assert r2.returncode == 2
    assert "REFUSED" in r2.stderr and "rate limit" in r2.stderr


def test_quiet_hours_block_acting(tmp_path, home):
    pol = write_policy(str(tmp_path / "policy.yaml"),
                       quiet_hours={"enabled": True, "start": "00:00",
                                    "end": "23:59"})
    add_account(home)
    r = cli("engage", "like", "--platform", "tiktok", "--account", "main",
            "--target", "v1", home=home, policy=pol)
    assert r.returncode == 2
    assert "quiet hours" in r.stderr
    # watchers (read-only) still work during quiet hours
    r = cli("watch", "list", home=home, policy=pol)
    assert r.returncode == 0


def test_approval_expiry(tmp_path, home):
    add_account(home)
    cli("engage", "like", "--platform", "tiktok", "--account", "main",
        "--target", "v1", home=home)
    actions = state(home, "actions.json")
    aid = actions[0]["id"]
    assert cli("engage", "approve", aid, home=home).returncode == 0
    # backdate the approval past the 24h expiry
    actions = state(home, "actions.json")
    actions[0]["approved_at_ts"] = time.time() - 25 * 3600
    import json
    with open(os.path.join(home, "actions.json"), "w", encoding="utf-8") as fh:
        json.dump(actions, fh)
    r = cli("engage", "done", aid, home=home)
    assert r.returncode == 2
    assert "expired" in r.stderr
    assert state(home, "actions.json")[0]["status"] == "expired"


def test_no_credentials_in_state(home):
    add_account(home, username="tester", label="main")
    accounts = state(home, "accounts.json")
    blob = str(accounts)
    for secret_word in ("password", "token", "secret", "cookie"):
        assert secret_word not in blob.lower()
