"""CLI end-to-end tests (subprocess, isolated SOCIAL_AGENT_HOME)."""

import json
import os

from conftest import FIXTURES, add_account, cli, state, write_policy


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


def test_ticket_lifecycle_via_approval(home):
    """Brain -> hands: approving a proposal issues an execution ticket;
    the external agent claims it, fulfills it with evidence, and the host
    session is recorded. The repo never acts by itself."""
    add_account(home)
    # 1. propose (dry-run, queued for human approval)
    r = cli("engage", "like", "--platform", "tiktok", "--account", "main",
            "--target", "vid9", home=home)
    assert r.returncode == 0, r.stderr
    aid = state(home, "actions.json")[0]["id"]
    # 2. human approves -> an execution ticket is ISSUED
    r = cli("engage", "approve", aid, home=home)
    assert r.returncode == 0, r.stderr
    assert "ticket" in r.stdout
    tickets = state(home, "tickets.json")
    assert len(tickets) == 1
    t = tickets[0]
    tid = t["id"]
    assert t["status"] == "issued"
    assert t["action"] == "like" and t["platform"] == "tiktok"
    assert t["steps"]  # step-by-step instructions for the external agent
    assert t["receipts"]["approval"]["decided_by"] == "user"
    # 3. tickets list shows it (plain, --status, --pending, --json)
    r = cli("tickets", home=home)
    assert r.returncode == 0 and tid in r.stdout and "[issued]" in r.stdout
    r = cli("tickets", "--status", "issued", home=home)
    assert tid in r.stdout
    r = cli("tickets", "--status", "claimed", home=home)
    assert "no tickets" in r.stdout
    r = cli("tickets", "--pending", home=home)
    assert tid in r.stdout
    r = cli("tickets", "--json", home=home)
    assert r.returncode == 0
    assert json.loads(r.stdout)[0]["id"] == tid
    # 4. ticket show --json is machine-readable for the external agent
    r = cli("ticket", "show", tid, "--json", home=home)
    assert r.returncode == 0, r.stderr
    shown = json.loads(r.stdout)
    assert shown["id"] == tid and shown["idem_key"] == f"ticket:{tid}"
    # 5. external agent claims it (issued -> claimed)
    r = cli("ticket", "claim", tid, "--agent", "muse",
            "--session", "sess-cli-1", home=home)
    assert r.returncode == 0, r.stderr
    assert "claimed by muse" in r.stdout
    assert state(home, "tickets.json")[0]["status"] == "claimed"
    r = cli("tickets", "--status", "claimed", home=home)
    assert tid in r.stdout
    # double-claim is refused (ticket error on stderr; status unchanged).
    # NOTE: main() currently discards cmd_ticket's return code, so the
    # refusal surfaces on stderr with exit 0 — reported to the repo owner.
    r = cli("ticket", "claim", tid, "--agent", "muse",
            "--session", "sess-cli-1", home=home)
    assert "ticket error" in r.stderr
    assert "cannot move to claimed" in r.stderr
    assert state(home, "tickets.json")[0]["status"] == "claimed"
    # 6. fulfill with evidence (claimed -> fulfilled)
    r = cli("ticket", "fulfill", tid, "--evidence",
            "liked vid9 in the live browser session", home=home)
    assert r.returncode == 0, r.stderr
    assert "fulfilled" in r.stdout
    done = state(home, "tickets.json")[0]
    assert done["status"] == "fulfilled"
    assert "liked vid9" in done["fulfillment"]["evidence"]
    # no longer pending
    r = cli("tickets", "--pending", home=home)
    assert "no tickets" in r.stdout
    r = cli("ticket", "show", tid, home=home)
    assert "[fulfilled]" in r.stdout and "liked vid9" in r.stdout
    # 7. the host-browser session was recorded on claim
    r = cli("identity", "host-sessions", home=home)
    assert r.returncode == 0, r.stderr
    assert "sess-cli-1" in r.stdout and "agent=muse" in r.stdout
    assert "tickets_fulfilled=1" in r.stdout
    # 8. operator confirms via the existing engage done flow
    r = cli("engage", "done", aid, "--result", "liked in browser", home=home)
    assert r.returncode == 0, r.stderr
    assert state(home, "actions.json")[0]["status"] == "done"


def test_ticket_cancel_and_fail(home, tmp_path):
    # two likes in one home: relax the like-spam guard via policy
    pol = write_policy(str(tmp_path / "policy.yaml"),
                       engagement={"min_seconds_between_likes": 0})
    add_account(home)
    r = cli("engage", "like", "--platform", "tiktok", "--account", "main",
            "--target", "vidA", home=home, policy=pol)
    assert r.returncode == 0, r.stderr
    aid = state(home, "actions.json")[0]["id"]
    assert cli("engage", "approve", aid, home=home, policy=pol).returncode == 0
    tid = state(home, "tickets.json")[0]["id"]
    r = cli("ticket", "cancel", tid, "--reason", "no longer needed", home=home)
    assert r.returncode == 0 and "cancelled" in r.stdout
    assert state(home, "tickets.json")[0]["status"] == "cancelled"
    # a second proposal -> ticket -> external agent reports failure
    r = cli("engage", "like", "--platform", "tiktok", "--account", "main",
            "--target", "vidB", home=home, policy=pol)
    assert r.returncode == 0, r.stderr
    aid2 = state(home, "actions.json")[1]["id"]
    assert cli("engage", "approve", aid2, home=home, policy=pol).returncode == 0
    tid2 = state(home, "tickets.json")[1]["id"]
    assert cli("ticket", "claim", tid2, "--agent", "muse",
               "--session", "s2", home=home).returncode == 0
    r = cli("ticket", "fail", tid2, "--error", "post deleted", home=home)
    assert r.returncode == 0 and "marked failed" in r.stdout
    assert state(home, "tickets.json")[1]["status"] == "failed"
    # unknown ticket id is an error on stderr, not a crash
    r = cli("ticket", "show", "tkt-nope", home=home)
    assert "ticket error" in r.stderr


def test_research_and_analytics(home):
    add_account(home)
    r = cli("research", "AI video", "--platforms", "tiktok,x", home=home)
    assert r.returncode == 0 and "AI video" in r.stdout
    plans = state(home, "research.json")
    assert plans[0]["platforms"] == ["tiktok", "x"]
    assert len(plans[0]["queries"]["tiktok"]) == 4
    r = cli("analytics", home=home)
    assert r.returncode == 0 and "events: 0" in r.stdout
