#!/usr/bin/env python3
"""Scenario exams for social-agent. Each exam runs the real CLI against an
isolated state dir, checks safety-critical behaviors, and records results.

Run:  python3 exams/run_exams.py
Appends: exams/RESULTS.md (one section per run; history is preserved)
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
    # isolate missions per exam so reruns never collide on mission names
    env["SOCIAL_AGENT_MISSIONS"] = os.path.join(home, "missions")
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
                                              "actions_per_day": 2}},
                       engagement={"min_seconds_between_likes": 0})
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


# ------------------------------------------------- new exams (upgrade) ---

def exam_7_selective_engagement():
    ex = Exam("exam-7", "Boring posts are NOT liked; interesting posts ARE (selective engagement)")
    home = fresh_home()
    setup_account(home)
    fx = os.path.join(FX, "feed_interest.json")
    r = run(home, None, "watch", "start", "--type", "feed", "--platform", "tiktok",
            "--account", "main", "--set", "use_interest_profile=true",
            "--set", "propose_engage=true",
            "--fixture", fx, "--id", "e7")
    ex.check("interest-filtered feed watcher starts", r.returncode == 0, r.stderr.strip())
    r = run(home, None, "watch", "run", "e7")
    ex.check("only 2 interesting posts emit events", "2 new event(s)" in r.stdout, r.stdout.strip())
    ex.check("boring/spam posts produce no proposals",
             "dancer_y" not in r.stdout and "crypto_giveaway" not in r.stdout,
             r.stdout.strip()[:300])
    ex.check("interesting posts propose likes", r.stdout.count("proposes: like") == 2,
             r.stdout.strip()[:300])
    # direct engage like on a boring post is refused with a reason
    r = run(home, None, "engage", "like", "--platform", "tiktok", "--account", "main",
            "--target", "boring1", "--author", "dancer_y",
            "--text", "POV: your cat pays rent", "--likes-count", "5")
    ex.check("boring like refused (exit 2)",
             r.returncode == 2 and "not interesting" in r.stderr, r.stderr.strip())
    refusals = [json.loads(l) for l in open(os.path.join(home, "refusals.jsonl"))]
    ex.check("refusal logged with reason", len(refusals) == 1 and "reason" in refusals[0],
             str(refusals[0])[:120])
    # interesting post like is proposed
    r = run(home, None, "engage", "like", "--platform", "tiktok", "--account", "main",
            "--target", "fi1", "--author", "creator_x",
            "--text", "New AI video workflow just dropped #aivideo",
            "--hashtags", "aivideo", "--likes-count", "500")
    ex.check("interesting like proposed", r.returncode == 0 and "DRY-RUN" in r.stdout,
             r.stderr.strip() or r.stdout.strip()[:120])
    return ex


def exam_8_like_spam_guards():
    ex = Exam("exam-8", "Like spam blocked: daily cap + per-author cooldown")
    home = fresh_home()
    pol = write_policy(os.path.join(home, "policy.yaml"),
                       engagement={"likes_per_day": 2, "likes_per_hour": 10,
                                   "like_author_cooldown_hours": 24,
                                   "min_seconds_between_likes": 0})
    setup_account(home)
    base = ["engage", "like", "--platform", "tiktok", "--account", "main"]
    post = ["--text", "sora ai video tutorial", "--likes-count", "500"]
    r1 = run(home, pol, *(base + ["--target", "v1", "--author", "author_a"] + post))
    ex.check("first like ok", r1.returncode == 0, r1.stderr.strip())
    r2 = run(home, pol, *(base + ["--target", "v2", "--author", "author_a"] + post))
    ex.check("same author twice blocked by cooldown",
             r2.returncode == 2 and "cooldown" in r2.stderr, r2.stderr.strip())
    r3 = run(home, pol, *(base + ["--target", "v3", "--author", "author_b"] + post))
    ex.check("second author ok (2/2 daily)", r3.returncode == 0, r3.stderr.strip())
    r4 = run(home, pol, *(base + ["--target", "v4", "--author", "author_c"] + post))
    ex.check("third like blocked by daily cap",
             r4.returncode == 2 and "daily like cap" in r4.stderr, r4.stderr.strip())
    return ex


def exam_9_autonomous_in_scope():
    ex = Exam("exam-9", "Autonomous post inside mission scope is auto-approved")
    home = fresh_home()
    setup_account(home)
    run(home, None, "mission", "create", "--name", "m9", "--platforms", "tiktok",
        "--topics", "ai video,sora", "--actions", "post,like",
        "--limit", "posts_per_day=2")
    r = run(home, None, "autonomy", "grant", "--mission", "m9")
    ex.check("grant without --confirm refused", r.returncode == 1, r.stderr.strip()[:80])
    r = run(home, None, "autonomy", "grant", "--mission", "m9", "--confirm")
    ex.check("grant with --confirm succeeds", r.returncode == 0 and "GRANTED" in r.stdout)
    run(home, None, "post", "draft", "--platform", "tiktok", "--account", "main",
        "--text", "sora ai video tutorial part 2", "--id", "ep9")
    run(home, None, "post", "queue", "ep9")
    r = run(home, None, "post", "approve", "ep9")
    q = state(home, "queue.json")[0]
    ex.check("in-scope post auto-approved", r.returncode == 0 and "AUTO-APPROVED" in r.stdout)
    ex.check("auto_approved + mission recorded",
             q.get("auto_approved") is True and q.get("mission") == "m9", str(q)[:150])
    return ex


def exam_10_scope_block():
    ex = Exam("exam-10", "Actions outside mission scope are blocked and logged")
    home = fresh_home()
    setup_account(home)
    run(home, None, "mission", "create", "--name", "m10", "--platforms", "tiktok",
        "--topics", "ai video", "--actions", "post,like")
    run(home, None, "autonomy", "grant", "--mission", "m10", "--confirm")
    r = run(home, None, "engage", "like", "--platform", "instagram",
            "--account", "main", "--target", "v1")
    ex.check("off-platform action blocked", r.returncode == 2 and "scope" in r.stderr,
             r.stderr.strip())
    run(home, None, "post", "draft", "--platform", "tiktok", "--account", "main",
        "--text", "my cat pays rent", "--id", "ep10")
    r = run(home, None, "post", "approve", "ep10")
    ex.check("off-topic post blocked", r.returncode == 2 and "scope" in r.stderr,
             r.stderr.strip())
    refusals = [json.loads(l) for l in open(os.path.join(home, "refusals.jsonl"))]
    ex.check("both blocks logged to refusals.jsonl", len(refusals) == 2,
             f"{len(refusals)} logged")
    return ex


def exam_11_profile_always_needs_approval():
    ex = Exam("exam-11", "Profile change blocked without approval even in autonomous mode")
    home = fresh_home()
    setup_account(home)
    run(home, None, "mission", "create", "--name", "m11", "--platforms", "tiktok",
        "--topics", "ai video", "--actions", "post,like")
    run(home, None, "autonomy", "grant", "--mission", "m11", "--confirm")
    r = run(home, None, "profile", "update", "--account", "main",
            "--display-name", "New Name")
    pid = state(home, "profiles.json")["proposals"][0]["id"]
    ex.check("update creates proposal (not auto-approved)",
             r.returncode == 0 and
             state(home, "profiles.json")["proposals"][0]["status"] == "proposed")
    ex.check("no auto_approved flag on profile proposal",
             state(home, "profiles.json")["proposals"][0].get("auto_approved") is not True)
    r = run(home, None, "profile", "approve", pid)
    ex.check("explicit profile approve works", r.returncode == 0 and "APPROVED" in r.stdout)
    return ex


def exam_12_heartbeat_protocol():
    ex = Exam("exam-12", "Watcher runs emit start+success; failures emit /fail")
    home = fresh_home()
    setup_account(home)
    fx = os.path.join(FX, "notifications.json")
    run(home, None, "watch", "start", "--type", "notification", "--platform", "tiktok",
        "--account", "main", "--fixture", fx, "--id", "e12")
    r = run(home, None, "watch", "run", "e12")
    ex.check("good watcher polls ok", r.returncode == 0, r.stderr.strip())
    hist = json.load(open(os.path.join(home, "heartbeat.json")))
    paths = [h["path"] for h in hist if h["name"] == "e12"]
    ex.check("start heartbeat recorded", any(p.endswith("/start") for p in paths), str(paths))
    ex.check("success heartbeat recorded",
             any(p == "e12" for p in paths), str(paths))
    ex.check("no /fail for good run", not any(p.endswith("/fail") for p in paths))
    # failing watcher: fixture that does not exist
    run(home, None, "watch", "start", "--type", "notification", "--platform", "tiktok",
        "--account", "main", "--fixture", "/nonexistent/fx.json", "--id", "e12bad")
    r = run(home, None, "watch", "run", "e12bad")
    ex.check("bad watcher run fails", r.returncode == 1, r.stderr.strip()[:100])
    hist = json.load(open(os.path.join(home, "heartbeat.json")))
    bad = [h["path"] for h in hist if h["name"] == "e12bad"]
    ex.check("/fail heartbeat recorded for failing run",
             any(p.endswith("/fail") for p in bad), str(bad))
    return ex


def exam_13_crisis_watcher():
    ex = Exam("exam-13", "Crisis watcher fires an urgent event on a negative spike")
    home = fresh_home()
    setup_account(home)
    fx = os.path.join(FX, "crisis.json")
    # stamp items into the detection window (fixture ships with fixed timestamps)
    import datetime as _dt
    items = json.load(open(fx))["items"]
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
    for it in items:
        it["timestamp"] = now
    live_fx = os.path.join(home, "crisis_live.json")
    json.dump({"items": items}, open(live_fx, "w"))
    r = run(home, None, "watch", "start", "--type", "crisis", "--platform", "tiktok",
            "--account", "main", "--set", "accounts=examuser",
            "--fixture", live_fx, "--id", "e13")
    ex.check("crisis watcher starts", r.returncode == 0, r.stderr.strip())
    r = run(home, None, "watch", "run", "e13")
    ex.check("spike detected", "1 new event(s)" in r.stdout, r.stdout.strip())
    ex.check("event is urgent", "urgent" in r.stdout.lower(), r.stdout.strip()[:200])
    return ex


def exam_14_trend_interest_filter():
    ex = Exam("exam-14", "Trend watcher filters out off-mission trends")
    home = fresh_home()
    setup_account(home)
    fx = os.path.join(FX, "trend.json")
    r = run(home, None, "watch", "start", "--type", "trend", "--platform", "tiktok",
            "--account", "main", "--set", "min_heat=60",
            "--set", "use_interest_profile=true",
            "--fixture", fx, "--id", "e14")
    ex.check("trend watcher starts", r.returncode == 0, r.stderr.strip())
    r = run(home, None, "watch", "run", "e14")
    ex.check("off-mission #dancetrend filtered out", "#dancetrend" not in r.stdout,
             r.stdout.strip()[:300])
    ex.check("on-mission trends proposed", "proposes: post" in r.stdout,
             r.stdout.strip()[:300])
    return ex


def exam_15_content_idea_aggregation():
    ex = Exam("exam-15", "Content-idea watcher aggregates repeated audience questions")
    home = fresh_home()
    setup_account(home)
    fx = os.path.join(FX, "content_idea.json")
    r = run(home, None, "watch", "start", "--type", "content-idea", "--platform", "tiktok",
            "--account", "main", "--fixture", fx, "--id", "e15")
    ex.check("content-idea watcher starts", r.returncode == 0, r.stderr.strip())
    r = run(home, None, "watch", "run", "e15")
    ex.check("one aggregated idea event", "1 new event(s)" in r.stdout, r.stdout.strip())
    ex.check("event names the repeated question",
             "sora camera moves tutorial" in r.stdout.lower(), r.stdout.strip()[:200])
    ex.check("proposes a post angle", "proposes: post" in r.stdout, r.stdout.strip()[:200])
    return ex

def exam_16_tos_scraping_refused():
    ex = Exam("exam-16", "ToS-prohibited data collection is refused before any poll")
    home = fresh_home()
    run(home, None, "accounts", "add", "--platform", "x",
        "--username", "examuser", "--label", "main")
    fx = os.path.join(FX, "notifications.json")
    r = run(home, None, "watch", "start", "--type", "notification", "--platform", "x",
            "--account", "main", "--fixture", fx, "--id", "e16")
    ex.check("watcher start refused (exit 2)", r.returncode == 2, r.stderr.strip())
    ex.check("refusal cites the Terms of Service",
             "ToS" in r.stderr, r.stderr.strip()[:160])
    ex.check("no watcher was registered",
             "e16" not in state(home, "watchers.json", {}))
    refusals = [json.loads(l) for l in open(os.path.join(home, "refusals.jsonl"))]
    ex.check("refusal logged with ToS reason",
             len(refusals) == 1 and "ToS" in refusals[0]["reason"],
             str(refusals[0])[:120] if refusals else "no refusals file")
    return ex



def exam_17_autonomy_cannot_override_tos():
    ex = Exam("exam-17", "An autonomous mission cannot override a ToS prohibition")
    home = fresh_home()
    run(home, None, "accounts", "add", "--platform", "x",
        "--username", "examuser", "--label", "main")
    run(home, None, "mission", "create", "--name", "m17", "--platforms", "x",
        "--topics", "ai video", "--actions", "like,post")
    r = run(home, None, "autonomy", "grant", "--mission", "m17", "--confirm")
    ex.check("autonomy granted", r.returncode == 0 and "GRANTED" in r.stdout,
             r.stderr.strip()[:80])
    r = run(home, None, "engage", "like", "--platform", "x",
            "--account", "main", "--target", "v1")
    ex.check("like refused despite autonomy (exit 2)", r.returncode == 2,
             r.stderr.strip()[:120])
    ex.check("refusal is a ToS refusal, not a scope block",
             "ToS" in r.stderr and "scope" not in r.stderr,
             r.stderr.strip()[:160])
    ex.check("no proposal was created", state(home, "actions.json", []) == [])
    refusals = [json.loads(l) for l in open(os.path.join(home, "refusals.jsonl"))]
    ex.check("refusal logged with ToS reason",
             len(refusals) == 1 and "ToS" in refusals[0]["reason"],
             str(refusals[0])[:120] if refusals else "no refusals file")
    return ex


def exam_18_restricted_action_proceeds_with_advisory():
    ex = Exam("exam-18", "A ToS-restricted action proceeds and shows the constraint")
    home = fresh_home()
    setup_account(home)
    fx = os.path.join(FX, "notifications.json")
    r = run(home, None, "watch", "start", "--type", "notification",
            "--platform", "tiktok", "--account", "main",
            "--fixture", fx, "--id", "e18")
    ex.check("watcher starts (exit 0)", r.returncode == 0, r.stderr.strip())
    ex.check("ToS advisory shown", "ToS note" in r.stderr,
             r.stderr.strip()[:160])
    r = run(home, None, "watch", "run", "e18")
    ex.check("poll proceeds", "4 new event(s)" in r.stdout, r.stdout.strip())
    return ex




# ------------------------------------------- growth/voice/security/study exams ---

def exam_19_voice_flags_ai_draft():
    ex = Exam("exam-19", "Voice check flags an AI-isms-laden draft")
    home = fresh_home()
    r = run(home, None, "voice", "check",
            "--text", "Delve into this game-changer: leverage these tips to unlock success!")
    ex.check("exit 0 (voice warns, never refuses)", r.returncode == 0, r.stderr.strip())
    ex.check("flags banned AI-isms", "delve" in r.stdout.lower(), r.stdout.strip()[:200])
    ex.check("score below clean threshold", "64/100" in r.stdout, r.stdout.strip()[:120])
    return ex


def exam_20_youtube_preflight_blocks():
    ex = Exam("exam-20", "YouTube preflight blocks a video post missing title/thumbnail")
    home = fresh_home()
    r = run(home, None, "youtube", "preflight", "--audio", "--captions")
    ex.check("preflight refused (exit 2)", r.returncode == 2, r.stderr.strip()[:160])
    ex.check("missing title named", "title" in r.stderr.lower(), r.stderr.strip()[:200])
    ex.check("missing thumbnail named", "thumbnail" in r.stderr.lower(), r.stderr.strip()[:200])
    return ex


def exam_21_youtube_titles_scored():
    ex = Exam("exam-21", "YouTube titles command returns 5 scored variants")
    home = fresh_home()
    r = run(home, None, "youtube", "titles", "my cat pays rent", "--keyword", "cat")
    ex.check("exit 0", r.returncode == 0, r.stderr.strip())
    lines = [l for l in r.stdout.splitlines() if l.startswith("[")]
    ex.check("exactly 5 variants", len(lines) == 5, r.stdout.strip()[:200])
    scores = [int(l.split("]")[0].strip("[ ")) for l in lines]
    ex.check("scores sorted desc", scores == sorted(scores, reverse=True), str(scores))
    return ex


def exam_22_study_produces_adjustments():
    ex = Exam("exam-22", "Study run derives adjustments from fixture analytics")
    home = fresh_home()
    events = [
        {"timestamp": "2026-09-25T00:00:00Z", "kind": "crisis:spike",
         "data": {"topics": ["audio quality"]}},
        {"timestamp": "2026-09-25T01:00:00Z", "kind": "content-idea:question",
         "data": {"topics": ["hooks"]}},
    ]
    with open(os.path.join(home, "events.jsonl"), "w", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")
    r = run(home, None, "study", "run")
    ex.check("exit 0", r.returncode == 0, r.stderr.strip())
    journal = os.path.join(home, "learning", "journal.md")
    ex.check("journal.md written", os.path.exists(journal))
    body = open(journal, encoding="utf-8").read()
    ex.check("journal reacts to the crisis spike", "crisis" in body.lower())
    ex.check("journal contains concrete adjustments",
             "3 concrete adjustments" in body, body[-300:])
    return ex


def exam_23_security_refuses_secret_draft():
    ex = Exam("exam-23", "Security gate refuses a draft containing a secret")
    home = fresh_home()
    setup_account(home)
    r = run(home, None, "post", "draft", "--platform", "tiktok", "--account", "main",
            "--text", "here is my api_key=sk-abcdefghij1234567890 use it")
    ex.check("draft refused (exit 2)", r.returncode == 2, r.stderr.strip()[:160])
    ex.check("refusal cites secret detection", "secret" in r.stderr.lower(),
             r.stderr.strip()[:160])
    ex.check("no draft was created", state(home, "queue.json", []) == [])
    refusals = [json.loads(l) for l in open(os.path.join(home, "refusals.jsonl"))]
    ex.check("refusal logged with secret reason",
             refusals and "secret" in refusals[0]["reason"].lower(),
             str(refusals[0])[:120] if refusals else "no refusals file")
    return ex


def exam_24_growth_audit_pillars():
    ex = Exam("exam-24", "Growth audit scores the 5 pillars and suggests fixes")
    home = fresh_home()
    r = run(home, None, "growth", "audit", "--platform", "youtube",
            "--account", "main", "--followers", "850", "--posts-per-week", "3",
            "--avg-views", "4200", "--avg-likes", "180", "--avg-comments", "12",
            "--niche", "AI video tutorials", "--has-bio", "--has-avatar", "--has-cta")
    ex.check("exit 0", r.returncode == 0, r.stderr.strip())
    for pillar in ("consistency", "hooks", "niche_clarity", "engagement_rate",
                   "profile_conversion"):
        ex.check(f"pillar scored: {pillar}", pillar in r.stdout, r.stdout.strip()[:200])
    ex.check("overall score shown", "overall:" in r.stdout)
    ex.check("fixes suggested", "fixes (worst first):" in r.stdout)
    return ex


def exam_25_identity_flags_ai_claim():
    ex = Exam("exam-25", "Identity check flags a draft claiming to be an AI")
    home = fresh_home()
    setup_account(home)
    r = run(home, None, "identity", "create", "--account", "main",
            "--name", "Exam Owner", "--voice-traits", "dry humor")
    ex.check("persona created", r.returncode == 0, r.stderr.strip())
    r = run(home, None, "identity", "check",
            "--text", "As an AI language model, I love this video!",
            "--account", "main")
    ex.check("identity check failed (exit 2)", r.returncode == 2, r.stderr.strip()[:160])
    ex.check("failure cites identity break", "identity break" in r.stderr.lower(),
             r.stderr.strip()[:200])
    return ex


def exam_26_identity_first_person_passes():
    ex = Exam("exam-26", "A good first-person owner draft passes identity check")
    home = fresh_home()
    setup_account(home)
    run(home, None, "identity", "create", "--account", "main",
        "--name", "Exam Owner", "--voice-traits", "dry humor",
        "--never-say", "smash that like button")
    r = run(home, None, "identity", "check",
            "--text", "I spent 11 minutes rendering this shot. My favorite part is the lighting.",
            "--account", "main")
    ex.check("identity check passed (exit 0)", r.returncode == 0, r.stderr.strip())
    ex.check("PASSED in output", "PASSED" in r.stdout, r.stdout.strip()[:120])
    r = run(home, None, "identity", "check",
            "--text", "Smash that like button guys!", "--account", "main")
    ex.check("persona never-say violation refused (exit 2)", r.returncode == 2,
             r.stderr.strip()[:160])
    return ex


def exam_27_post_draft_identity_refused():
    ex = Exam("exam-27", "post draft with identity-breaking text is refused end-to-end")
    home = fresh_home()
    setup_account(home)
    run(home, None, "identity", "create", "--account", "main", "--name", "Exam Owner")
    r = run(home, None, "post", "draft", "--platform", "tiktok", "--account", "main",
            "--text", "As an AI language model, here is my post")
    ex.check("draft refused (exit 2)", r.returncode == 2, r.stderr.strip()[:160])
    ex.check("refusal cites identity", "identity" in r.stderr.lower(),
             r.stderr.strip()[:160])
    ex.check("no draft was created", state(home, "queue.json", []) == [])
    refusals = [json.loads(l) for l in open(os.path.join(home, "refusals.jsonl"))]
    ex.check("refusal logged to refusals.jsonl with identity reason",
             refusals and "identity" in refusals[0]["reason"].lower(),
             str(refusals[0])[:140] if refusals else "no refusals file")
    return ex



EXAMS = [exam_1_watcher_proposes_without_acting,
         exam_2_engage_blocked_without_approval,
         exam_3_rate_limit_enforced,
         exam_4_quiet_hours,
         exam_5_approval_lifecycle,
         exam_6_post_needs_approval,
         exam_7_selective_engagement,
         exam_8_like_spam_guards,
         exam_9_autonomous_in_scope,
         exam_10_scope_block,
         exam_11_profile_always_needs_approval,
         exam_12_heartbeat_protocol,
         exam_13_crisis_watcher,
         exam_14_trend_interest_filter,
         exam_15_content_idea_aggregation,
         exam_16_tos_scraping_refused,
         exam_17_autonomy_cannot_override_tos,
         exam_18_restricted_action_proceeds_with_advisory,
         exam_19_voice_flags_ai_draft,
         exam_20_youtube_preflight_blocks,
         exam_21_youtube_titles_scored,
         exam_22_study_produces_adjustments,
         exam_23_security_refuses_secret_draft,
         exam_24_growth_audit_pillars,
         exam_25_identity_flags_ai_claim,
         exam_26_identity_first_person_passes,
         exam_27_post_draft_identity_refused]


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
    entry = "\n".join(lines).rstrip("\n") + "\n"
    if os.path.exists(out):
        # Append: every run is recorded, history is never overwritten.
        with open(out, encoding="utf-8") as fh:
            prev = fh.read().rstrip("\n")
        entry = prev + "\n\n---\n\n" + entry
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(entry)
    print(f"wrote {out}: {total_score}/{total_possible}")
    for ex in results:
        print(f"  {ex.name}: {ex.score}/{ex.total}")
    return 0 if total_score == total_possible else 1


if __name__ == "__main__":
    sys.exit(main())
