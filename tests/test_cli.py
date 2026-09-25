"""CLI end-to-end tests (subprocess, isolated SOCIAL_AGENT_HOME)."""

import json
import os

from conftest import FIXTURES, add_account, cli, state


def test_doctor_passes(home):
    r = cli("doctor", home=home)
    assert r.returncode == 0, r.stderr
    assert "all checks passed" in r.stdout


def test_accounts_crud(home):
    add_account(home)
    r = cli("accounts", "list", home=home)
    assert "tester" in r.stdout and "tiktok" in r.stdout
    r = cli("accounts", "show", "main", home=home)
    assert r.returncode == 0 and "tester" in r.stdout
    # duplicate add fails
    r = cli("accounts", "add", "--platform", "tiktok", "--username", "tester", home=home)
    assert r.returncode == 1
    # unknown platform fails
    r = cli("accounts", "add", "--platform", "myspace", "--username", "x", home=home)
    assert r.returncode == 1
    r = cli("accounts", "remove", "tester", home=home)
    assert r.returncode == 0
    r = cli("accounts", "list", home=home)
    assert "tester" not in r.stdout


def test_watch_lifecycle_and_idempotency(home):
    add_account(home)
    fx = os.path.join(FIXTURES, "notifications.json")
    r = cli("watch", "start", "--type", "notification", "--platform", "tiktok",
            "--account", "main", "--fixture", fx, "--id", "w1", home=home)
    assert r.returncode == 0, r.stderr
    r = cli("watch", "run", "w1", home=home)
    assert r.returncode == 0
    assert "4 new event(s)" in r.stdout
    # idempotent: same fixture again -> zero new events
    r = cli("watch", "run", "w1", home=home)
    assert "0 new event(s)" in r.stdout
    r = cli("watch", "events", "--watcher", "w1", home=home)
    assert r.stdout.count("notification:") == 4
    r = cli("watch", "stop", "w1", home=home)
    assert r.returncode == 0
    r = cli("watch", "run", "w1", home=home)
    assert r.returncode == 1 and "stopped" in r.stderr


def test_watch_bad_config_rejected(home):
    add_account(home)
    # unknown watcher type
    r = cli("watch", "start", "--type", "nope", "--platform", "tiktok",
            "--account", "main", home=home)
    assert r.returncode == 1
    # missing required config (comment watcher needs post_id)
    r = cli("watch", "start", "--type", "comment", "--platform", "tiktok",
            "--account", "main", home=home)
    assert r.returncode == 1 and "post_id" in r.stderr
    # unknown account
    r = cli("watch", "start", "--type", "feed", "--platform", "tiktok",
            "--account", "ghost", home=home)
    assert r.returncode == 1


def test_post_flow(home):
    add_account(home)
    assert cli("post", "draft", "--platform", "tiktok", "--account", "main",
               "--text", "hello", "--id", "p1", home=home).returncode == 0
    assert cli("post", "queue", "p1", home=home).returncode == 0
    r = cli("post", "approve", "p1", home=home)
    assert r.returncode == 0
    assert "DRY-RUN" in r.stdout
    q = state(home, "queue.json")
    assert q[0]["status"] == "approved"
    # double-approve fails
    assert cli("post", "approve", "p1", home=home).returncode == 1
    # unknown post fails
    assert cli("post", "approve", "px", home=home).returncode == 1


def test_engage_dry_run_default_and_approval_gate(home):
    add_account(home)
    r = cli("engage", "like", "--platform", "tiktok", "--account", "main",
            "--target", "vid1", home=home)
    assert r.returncode == 0
    assert "DRY-RUN" in r.stdout and "No action was taken" in r.stdout
    actions = state(home, "actions.json")
    assert actions[0]["status"] == "proposed" and actions[0]["dry_run"] is True
    aid = actions[0]["id"]
    # done without approval is refused
    r = cli("engage", "done", aid, home=home)
    assert r.returncode == 1 and "approve it first" in r.stderr
    # approve then done works
    assert cli("engage", "approve", aid, home=home).returncode == 0
    r = cli("engage", "done", aid, "--result", "liked in browser", home=home)
    assert r.returncode == 0
    assert state(home, "actions.json")[0]["status"] == "done"


def test_engage_comment_requires_text(home):
    add_account(home)
    r = cli("engage", "comment", "--platform", "tiktok", "--account", "main",
            "--target", "vid1", home=home)
    assert r.returncode == 1 and "--text" in r.stderr


def test_research_and_analytics(home):
    add_account(home)
    r = cli("research", "AI video", "--platforms", "tiktok,x", home=home)
    assert r.returncode == 0 and "AI video" in r.stdout
    plans = state(home, "research.json")
    assert plans[0]["platforms"] == ["tiktok", "x"]
    assert len(plans[0]["queries"]["tiktok"]) == 4
    r = cli("analytics", home=home)
    assert r.returncode == 0 and "events: 0" in r.stdout
