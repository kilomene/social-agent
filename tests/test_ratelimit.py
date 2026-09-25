"""Central rate-limit controller tests: windows, overrides, escalation."""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ratelimit import controller as rl
from conftest import add_account, cli, state, write_policy


def _policy(**over):
    return {"rate_limits": over}


def test_check_consume_window(tmp_path):
    home = str(tmp_path / "home")
    pol = _policy(tiktok={"like": {"per_hour": 2, "per_day": 5}})
    assert rl.check(home, "tiktok", "like", pol)["allowed"]
    rl.consume(home, "tiktok", "like")
    rl.consume(home, "tiktok", "like")
    verdict = rl.check(home, "tiktok", "like", pol)
    assert not verdict["allowed"]
    assert verdict["retry_at"] > time.time()
    assert verdict["remaining_hour"] == 0


def test_buckets_independent_per_platform_and_action(tmp_path):
    home = str(tmp_path / "home")
    pol = _policy(tiktok={"like": {"per_hour": 1, "per_day": 5}},
                  x={"like": {"per_hour": 1, "per_day": 5}})
    rl.consume(home, "tiktok", "like")
    assert not rl.check(home, "tiktok", "like", pol)["allowed"]
    assert rl.check(home, "x", "like", pol)["allowed"]
    assert rl.check(home, "tiktok", "comment", pol)["allowed"]


def test_action_overrides_fall_back_to_platform_default(tmp_path):
    home = str(tmp_path / "home")
    pol = _policy(tiktok={"per_hour": 3, "per_day": 30})
    for _ in range(3):
        rl.consume(home, "tiktok", "comment")
    assert not rl.check(home, "tiktok", "comment", pol)["allowed"]
    assert rl.check(home, "tiktok", "like", pol)["allowed"]


def test_denial_escalation_widens_retry(tmp_path):
    home = str(tmp_path / "home")
    pol = _policy(tiktok={"like": {"per_hour": 1, "per_day": 5}})
    rl.consume(home, "tiktok", "like")
    r1 = rl.check(home, "tiktok", "like", pol)["retry_at"]
    time.sleep(0.01)
    r2 = rl.check(home, "tiktok", "like", pol)["retry_at"]
    assert r2 > r1  # consecutive denials widen the retry window


def test_status_reports_remaining(tmp_path):
    home = str(tmp_path / "home")
    pol = _policy(tiktok={"like": {"per_hour": 4, "per_day": 10}})
    rl.consume(home, "tiktok", "like")
    rows = rl.status(home, pol)
    row = next(r for r in rows if r["bucket"] == "tiktok:like")
    assert row["remaining_hour"] == 3
    assert row["remaining_day"] == 9


def test_cli_exhaustion_queues_rate_limited(tmp_path, home):
    pol = write_policy(str(tmp_path / "policy.yaml"),
                       rate_limits={"tiktok": {"hide": {"per_hour": 1,
                                                       "per_day": 10}}})
    add_account(home)
    r = cli("moderate", "hide", "--platform", "tiktok", "--account", "main",
            "--post", "p1", "--comment", "c1", "--text", "ok comment",
            home=home, policy=pol)
    assert r.returncode == 0, r.stderr
    r = cli("moderate", "hide", "--platform", "tiktok", "--account", "main",
            "--post", "p1", "--comment", "c2", "--text", "another ok comment",
            home=home, policy=pol)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "rate limit" in r.stderr.lower()
    # underlying moderation log keeps exactly 1 record; the denied action is
    # queued in the approval queue as rate_limited, never dropped
    assert len(state(home, "moderation.json")) == 1
    items = state(home, "approvals/pending.json")
    rl_items = [i for i in items if i["status"] == "rate_limited"]
    assert len(rl_items) == 1
    assert rl_items[0]["retry_at"] > time.time()
