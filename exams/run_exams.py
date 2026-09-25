#!/usr/bin/env python3
"""Scenario exams for social-agent. Each exam runs the real CLI against an
isolated state dir, checks safety-critical behaviors, and records results.

Run:  python3 exams/run_exams.py
Writes: exams/RESULTS.md
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(REPO, "bin", "social-agent")
FX = os.path.join(REPO, "watchers", "fixtures")
sys.path.insert(0, os.path.join(REPO, "tests"))
from conftest import write_policy  # noqa: E402


def run(home, policy, *args):
    env = dict(os.environ, SOCIAL_AGENT_HOME=home)
    if policy:
        env["SOCIAL_AGENT_POLICY"] = policy
    return subprocess.run([sys.executable, CLI, *args],
                          capture_output=True, text=True, env=env)


def state(home, name, default=None):
    p = os.path.join(home, name)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


class Exam:
    def __init__(self, name, desc):
        self.name = name
        self.desc = desc
        self.checks = []  # (label, passed, detail)

    def check(self, label, passed, detail=""):
        self.checks.append((label, bool(passed), detail))

    @property
    def score(self):
        return sum(1 for _, p, _ in self.checks if p)

    @property
    def total(self):
        return len(self.checks)


def fresh_home():
    return tempfile.mkdtemp(prefix="sa-exam-")


def setup_account(home):
    r = run(home, None, "accounts", "add", "--platform", "tiktok",
            "--username", "examuser", "--label", "main")
    assert r.returncode == 0, r.stderr


# ------------------------------------------------------------- exams ---

def exam_1_watcher_proposes_without_acting():
    ex = Exam("exam-1", "Watcher detects new comment and proposes a reply without acting")
    home = fresh_home()
    setup_account(home)
    fx = os.path.join(FX, "comments.json")
    r = run(home, None, "watch", "start", "--type", "comment", "--platform", "tiktok",
            "--account", "main", "--set", "post_id=vid9", "--set", "propose_reply=true",
            "--fixture", fx, "--id", "ew1")
    ex.check("watcher starts", r.returncode == 0, r.stderr.strip())
    r = run(home, None, "watch", "run", "ew1")
    ex.check("poll finds 3 comments", "3 new event(s)" in r.stdout, r.stdout.strip())
    ex.check("events propose replies", "proposes: reply" in r.stdout, r.stdout.strip()[:200])
    actions = state(home, "actions.json", [])
    ex.check("no acting operation was created", actions == [], f"{len(actions)} actions")
    events = [json.loads(l) for l in open(os.path.join(home, "events.jsonl"))]
    ex.check("events logged for audit", len(events) == 3, f"{len(events)} logged")
    return ex


def exam_2_engage_blocked_without_approval():
    ex = Exam("exam-2", "Engagement is blocked until explicitly approved")
    home = fresh_home()
    setup_account(home)
    r = run(home, None, "engage", "like", "--platform", "tiktok",
            "--account", "main", "--target", "vid9")
    aid = state(home, "actions.json")[0]["id"]
    ex.check("proposal created as dry-run", r.returncode == 0 and "DRY-RUN" in r.stdout)
    ex.check("proposal status is 'proposed'",
             state(home, "actions.json")[0]["status"] == "proposed")
    r = run(home, None, "engage", "done", aid)
    ex.check("done without approval is refused",
             r.returncode == 1 and "approve it first" in r.stderr, r.stderr.strip())
    ex.check("status unchanged after refused done",
             state(home, "actions.json")[0]["status"] == "proposed")
    return ex


def exam_3_rate_limit_enforced():
    ex = Exam("exam-3", "Per-platform rate limits refuse excess actions")
    home = fresh_home()
    pol = write_policy(os.path.join(home, "policy.yaml"),
                       rate_limits={"tiktok": {"actions_per_hour": 2,
                                              "actions_per_day": 2}})
    setup_account(home)
    ok1 = run(home, pol, "engage", "like", "--platform", "tiktok",
              "--account", "main", "--target", "v1").returncode == 0
    ok2 = run(home, pol, "engage", "like", "--platform", "tiktok",
              "--account", "main", "--target", "v2").returncode == 0
    ex.check("actions within cap are allowed", ok1 and ok2)
    r = run(home, pol, "engage", "like", "--platform", "tiktok",
            "--account", "main", "--target", "v3")
    ex.check("third action refused with exit 2",
             r.returncode == 2 and "rate limit" in r.stderr, r.stderr.strip())
    n = len(state(home, "actions.json", []))
    ex.check("refused action left no proposal record", n == 2, f"{n} proposals")
    return ex


def exam_4_quiet_hours():
    ex = Exam("exam-4", "Quiet hours pause acting but not monitoring")
    home = fresh_home()
    pol = write_policy(os.path.join(home, "policy.yaml"),
                       quiet_hours={"enabled": True, "start": "00:00", "end": "23:59"})
    setup_account(home)
    r = run(home, pol, "engage", "follow", "--platform", "tiktok",
            "--account", "main", "--target", "someuser")
    ex.check("acting refused during quiet hours",
             r.returncode == 2 and "quiet hours" in r.stderr, r.stderr.strip())
    fx = os.path.join(FX, "notifications.json")
    run(home, pol, "watch", "start", "--type", "notification", "--platform", "tiktok",
        "--account", "main", "--fixture", fx, "--id", "ew4")
    r = run(home, pol, "watch", "run", "ew4")
    ex.check("read-only watcher still polls", "4 new event(s)" in r.stdout, r.stdout.strip())
    return ex


def exam_5_approval_lifecycle():
    ex = Exam("exam-5", "Full lifecycle: propose -> approve -> done is audited")
    home = fresh_home()
    setup_account(home)
    run(home, None, "engage", "comment", "--platform", "tiktok", "--account", "main",
        "--target", "vid9", "--text", "Great breakdown!")
    aid = state(home, "actions.json")[0]["id"]
    r = run(home, None, "engage", "approve", aid)
    ex.check("explicit approval succeeds", r.returncode == 0, r.stderr.strip())
    ex.check("approval timestamp recorded",
             "approved_at" in state(home, "actions.json")[0])
    r = run(home, None, "engage", "done", aid, "--result", "commented in browser")
    ex.check("done logs the externally performed action", r.returncode == 0)
    final = state(home, "actions.json")[0]
    ex.check("final status is done with result",
             final["status"] == "done" and final["result"] == "commented in browser",
             str(final))
    return ex


def exam_6_post_needs_approval():
    ex = Exam("exam-6", "Posts cannot skip the approval gate")
    home = fresh_home()
    setup_account(home)
    run(home, None, "post", "draft", "--platform", "tiktok", "--account", "main",
        "--text", "exam post", "--id", "ep1")
    q = state(home, "queue.json")[0]
    ex.check("draft starts unapproved", q["status"] == "draft")
    r = run(home, None, "post", "queue", "ep1")
    ex.check("queue does not approve", r.returncode == 0 and
             state(home, "queue.json")[0]["status"] == "queued")
    r = run(home, None, "post", "approve", "ep1")
    ex.check("explicit approve works and stays dry-run",
             r.returncode == 0 and "DRY-RUN" in r.stdout)
    ex.check("no post is ever published by the CLI",
             "never posts by itself" in r.stdout, r.stdout.strip()[-80:])
    return ex


EXAMS = [exam_1_watcher_proposes_without_acting,
         exam_2_engage_blocked_without_approval,
         exam_3_rate_limit_enforced,
         exam_4_quiet_hours,
         exam_5_approval_lifecycle,
         exam_6_post_needs_approval]


def main():
    results = [fn() for fn in EXAMS]
    total_score = sum(e.score for e in results)
    total_possible = sum(e.total for e in results)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# social-agent exam results",
        "",
        f"Run: {stamp} — all exams execute the real CLI against isolated state dirs.",
        "",
        f"**Total: {total_score}/{total_possible} "
        f"({100 * total_score // total_possible}%)**",
        "",
    ]
    for ex in results:
        mark = "PASS" if ex.score == ex.total else "FAIL"
        lines.append(f"## {ex.name}: {ex.desc}")
        lines.append(f"Score: **{ex.score}/{ex.total}** [{mark}]")
        for label, passed, detail in ex.checks:
            tick = "✓" if passed else "✗"
            extra = f" — {detail}" if detail and not passed else ""
            lines.append(f"- {tick} {label}{extra}")
        lines.append("")
    out = os.path.join(REPO, "exams", "RESULTS.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {out}: {total_score}/{total_possible}")
    for ex in results:
        print(f"  {ex.name}: {ex.score}/{ex.total}")
    return 0 if total_score == total_possible else 1


if __name__ == "__main__":
    sys.exit(main())
