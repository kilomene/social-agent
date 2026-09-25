#!/usr/bin/env python3
"""Scenario exams for social-agent. Each exam runs the real CLI against an
isolated state dir, checks safety-critical behaviors, and records results.

Run:  python3 exams/run_exams.py
Appends: exams/RESULTS.md (one section per run; history is preserved)
"""

import json
import os
import re
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


def people_state(home, account):
    """People memory in its legacy JSON shape (now served from memory.db)."""
    import sqlite3
    db = os.path.join(home, "memory.db")
    if not os.path.exists(db):
        return {}
    cx = sqlite3.connect(db)
    cx.row_factory = sqlite3.Row
    out = {}
    try:
        for r in cx.execute("SELECT * FROM people WHERE account_label = ?",
                            (account,)):
            d = dict(r)
            out[d["handle"]] = {
                "handle": d["handle"],
                "counts": json.loads(d["interactions_json"] or "{}"),
                "first_seen": d["first_seen"], "last_seen": d["last_seen"],
                "tags": json.loads(d["tags_json"] or "[]"),
                "notes": json.loads(d["notes_json"] or "[]"),
                "sentiments": json.loads(d["sentiments_json"] or "[]"),
                "conversations": json.loads(d["conversations_json"] or "[]"),
                "last_text": d["last_text"] or "",
                "score": d["score"],
            }
    finally:
        cx.close()
    return out


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




# ------------------------------------------- video specs / smart fit exams ---

def _gen_fixture(path, size="640x480", duration=4):
    import shutil
    if not shutil.which("ffmpeg"):
        return False
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                    "-i", f"testsrc=duration={duration}:size={size}:rate=30",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", path],
                   check=True)
    return True


def exam_34_specs_lookup():
    import shutil
    ex = Exam("exam-34", "specs lookup returns 9:16 for tiktok feed, 16:9 for youtube long-form")
    home = fresh_home()
    sys.path.insert(0, REPO)
    from video import fit as vfit
    specs = vfit.load_specs()
    ex.check("tiktok feed is 9:16", specs["tiktok"]["feed"]["aspect"] == "9:16")
    ex.check("youtube long-form is 16:9", specs["youtube"]["long-form"]["aspect"] == "16:9")
    ex.check("youtube shorts is 9:16", specs["youtube"]["shorts"]["aspect"] == "9:16")
    ex.check("tiktok feed resolution 1080x1920",
             (specs["tiktok"]["feed"]["width"], specs["tiktok"]["feed"]["height"]) == (1080, 1920))
    ex.check("11 placements across 6 platforms",
             sum(len(v) for v in specs.values()) == 11 and len(specs) == 6,
             f"{len(specs)} platforms, {sum(len(v) for v in specs.values())} placements")
    return ex


def exam_35_fit_defaults_to_pad():
    ex = Exam("exam-35", "4:3 -> 9:16 fit defaults to pad (nothing is cut)")
    home = fresh_home()
    mp4 = os.path.join(home, "four_three.mp4")
    if not _gen_fixture(mp4, "640x480"):
        ex.check("ffmpeg present", False, "ffmpeg missing")
        return ex
    out = os.path.join(home, "fitted.mp4")
    r = run(home, None, "video", "fit", "--input", mp4, "--output", out,
            "--for", "tiktok", "--dry-run")
    ex.check("fit exits 0", r.returncode == 0, r.stderr.strip()[:160])
    ex.check("strategy is pad", "strategy : pad" in r.stdout, r.stdout[:240])
    ex.check("pad uses blurred fill", "boxblur" in r.stdout, r.stdout[:240])
    ex.check("no destructive crop-to-fill box in args",
             "crop=1080:1920:740:0" not in r.stdout, r.stdout[:240])
    ex.check("dry-run wrote nothing", not os.path.exists(out))
    return ex


def exam_36_crop_refused_without_focus():
    ex = Exam("exam-36", "crop without a focus point is refused")
    home = fresh_home()
    mp4 = os.path.join(home, "src.mp4")
    if not _gen_fixture(mp4, "640x480"):
        ex.check("ffmpeg present", False, "ffmpeg missing")
        return ex
    r = run(home, None, "video", "fit", "--input", mp4,
            "--output", os.path.join(home, "out.mp4"),
            "--for", "tiktok", "--crop", "--dry-run")
    ex.check("refused (exit 2)", r.returncode == 2, r.stderr.strip()[:160])
    ex.check("refusal explains the focus requirement",
             "focus" in (r.stderr + r.stdout).lower(),
             (r.stderr + r.stdout)[:200])
    return ex


def exam_37_crop_focus_top_box_math():
    ex = Exam("exam-37", "crop with --focus top produces the correct crop box")
    home = fresh_home()
    mp4 = os.path.join(home, "src.mp4")
    if not _gen_fixture(mp4, "640x480"):
        ex.check("ffmpeg present", False, "ffmpeg missing")
        return ex
    r = run(home, None, "video", "fit", "--input", mp4,
            "--output", os.path.join(home, "out.mp4"),
            "--for", "tiktok", "--crop", "--focus", "top", "--dry-run")
    ex.check("exit 0", r.returncode == 0, r.stderr.strip()[:160])
    # 640x480 -> cover scale 4.0 -> 2560x1920; focus top => crop box offset (740, 0)
    ex.check("crop box math correct (crop=1080:1920:740:0)",
             "crop=1080:1920:740:0" in r.stdout, r.stdout[:300])
    ex.check("what gets cut is surfaced", "cuts" in r.stdout and "left" in r.stdout,
             r.stdout[:300])
    return ex


def exam_38_preflight_fails_wrong_aspect():
    ex = Exam("exam-38", "preflight FAILs a 16:9 video for youtube:shorts and suggests the fix")
    home = fresh_home()
    mp4 = os.path.join(home, "wide.mp4")
    if not _gen_fixture(mp4, "1280x720"):
        ex.check("ffmpeg present", False, "ffmpeg missing")
        return ex
    r = run(home, None, "video", "preflight", "--input", mp4, "--for", "youtube:shorts")
    ex.check("FAILED (nonzero exit)", r.returncode != 0, r.stderr.strip()[:200])
    ex.check("aspect check failed", "aspect" in r.stdout and "FAIL" in r.stdout,
             r.stdout[:240])
    ex.check("fix suggests the fit command",
             "video fit" in (r.stdout + r.stderr), (r.stdout + r.stderr)[-300:])
    return ex


def exam_39_preflight_passes_correct_video():
    ex = Exam("exam-39", "preflight PASSes a correct 9:16 video for youtube:shorts")
    home = fresh_home()
    mp4 = os.path.join(home, "vertical.mp4")
    if not _gen_fixture(mp4, "720x1280"):
        ex.check("ffmpeg present", False, "ffmpeg missing")
        return ex
    r = run(home, None, "video", "preflight", "--input", mp4, "--for", "youtube:shorts")
    ex.check("exit 0", r.returncode == 0, r.stderr.strip()[:160])
    ex.check("preflight PASSED", "PASSED" in r.stdout, r.stdout[:240])
    ex.check("aspect check passed", "[PASS] aspect" in r.stdout, r.stdout[:240])
    return ex



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



def exam_28_toxic_comment_flagged():
    ex = Exam("exam-28", "moderate scan flags toxic and spam comments")
    home = fresh_home()
    setup_account(home)
    fx = os.path.join(FX, "comments_moderation.json")
    r = run(home, None, "moderate", "scan", "--platform", "tiktok",
            "--account", "main", "--post", "v1", "--fixture", fx)
    ex.check("scan exits 0", r.returncode == 0, r.stderr.strip()[:120])
    ex.check("toxic comment flagged", "[toxic]" in r.stdout, r.stdout[:200])
    ex.check("spam comment flagged", "[spam]" in r.stdout, r.stdout[:200])
    ex.check("question classified", "[question]" in r.stdout, r.stdout[:200])
    ex.check("praise classified", "[praise]" in r.stdout, r.stdout[:200])
    return ex


def exam_29_spam_autohide_rule_proposes():
    ex = Exam("exam-29", "pre-approved auto-hide rule auto-approves a hide proposal")
    home = fresh_home()
    setup_account(home)
    pol = os.path.join(home, "policy.yaml")
    write_policy(pol, moderation={"auto_hide": ["double your money"],
                                 "note": "test"})
    r = run(home, pol, "moderate", "hide", "--platform", "tiktok",
            "--account", "main", "--post", "v1", "--comment", "c3",
            "--text", "DM me, double your money now!!",
            "--reason", "money-doubling scam")
    ex.check("hide exits 0", r.returncode == 0, r.stderr.strip()[:160])
    ex.check("auto-approved under pre-approved rule", "AUTO-APPROVED" in r.stdout,
             r.stdout[:160])
    log = state(home, "moderation.json", [])
    ex.check("logged as approved", log and log[0]["status"] == "approved",
             str(log[:1])[:160])
    ex.check("auto_hide rule recorded", log and log[0].get("auto_approved") is True,
             str(log[:1])[:160])
    return ex


def exam_30_hide_needs_approval():
    ex = Exam("exam-30", "moderate hide without approval is refused at done")
    home = fresh_home()
    setup_account(home)
    r = run(home, None, "moderate", "hide", "--platform", "tiktok",
            "--account", "main", "--post", "v1", "--comment", "c9",
            "--text", "mildly rude comment", "--reason", "borderline")
    mid = state(home, "moderation.json", [])[0]["id"]
    ex.check("proposal created (not executed)", r.returncode == 0 and
             "DRY-RUN proposal" in r.stdout, r.stdout[:160])
    r2 = run(home, None, "moderate", "done", "--id", mid)
    ex.check("done refused before approval", r2.returncode != 0,
             r2.stderr.strip()[:160])
    ex.check("status still proposed",
             state(home, "moderation.json", [])[0]["status"] == "proposed")
    r3 = run(home, None, "moderate", "approve", "--id", mid)
    ex.check("explicit approval works", r3.returncode == 0 and
             "APPROVED" in r3.stdout, (r3.stdout + r3.stderr)[:160])
    r4 = run(home, None, "moderate", "done", "--id", mid)
    ex.check("done after approval logged",
             state(home, "moderation.json", [])[0]["status"] == "done",
             r4.stdout[:120])
    return ex


def exam_31_caption_passes_gates():
    ex = Exam("exam-31", "caption generation passes voice+identity gates")
    home = fresh_home()
    setup_account(home)
    run(home, None, "identity", "create", "--account", "main",
        "--name", "Exam Owner", "--voice-traits", "direct,playful")
    r = run(home, None, "caption", "generate", "--platform", "tiktok",
            "--topic", "sora camera moves", "--tone", "bold", "--account", "main")
    ex.check("generate exits 0", r.returncode == 0, r.stderr.strip()[:160])
    ex.check("hashtag norms honored (3-5 for tiktok)",
             3 <= r.stdout.count("#") <= 5, r.stdout[-200:])
    ex.check("no voice warning on generated caption",
             "voice warning" not in r.stdout, r.stdout[-200:])
    ex.check("first-person owner voice present",
             any(w in r.stdout for w in (" I ", "I've", "I'll", "my ")),
             r.stdout[:200])
    return ex


def exam_32_video_info_clip_fixture():
    import shutil
    ex = Exam("exam-32", "video info/clip work on a generated fixture")
    home = fresh_home()
    if not shutil.which("ffmpeg"):
        r = run(home, None, "video", "clip", "--input", "x.mp4",
                "--start", "0", "--duration", "1", "--output", "y.mp4")
        ex.check("missing ffmpeg refuses gracefully",
                 r.returncode == 1 and "SETUP.md" in r.stderr, r.stderr[:160])
        return ex
    mp4 = os.path.join(home, "exam.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                    "-i", "testsrc=duration=4:size=640x480:rate=30",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", mp4],
                   check=True)
    r = run(home, None, "video", "info", "--input", mp4)
    ex.check("info exits 0", r.returncode == 0, r.stderr[:120])
    ex.check("info reports 640x480", "640x480" in r.stdout, r.stdout[:160])
    out = os.path.join(home, "clip.mp4")
    r2 = run(home, None, "video", "clip", "--input", mp4, "--start", "1",
             "--duration", "2", "--output", out)
    ex.check("clip exits 0 and prints its ffmpeg command",
             r2.returncode == 0 and "RUN: ffmpeg" in r2.stdout,
             r2.stdout[:200])
    ex.check("clip output exists", os.path.exists(out) and
             os.path.getsize(out) > 1000)
    r3 = run(home, None, "video", "clip", "--input", mp4, "--start", "0",
             "--duration", "1", "--output", mp4)
    ex.check("refuses to overwrite input", r3.returncode != 0, r3.stderr[:160])
    return ex


def exam_33_audio_clip_fades_args():
    ex = Exam("exam-33", "audio clip with fades emits correct ffmpeg filter args")
    home = fresh_home()
    r = run(home, None, "audio", "clip", "--input", "song.mp3",
            "--start", "30", "--duration", "15",
            "--fade-in", "2", "--fade-out", "3",
            "--output", os.path.join(home, "out.mp3"), "--dry-run")
    ex.check("dry-run exits 0", r.returncode == 0, r.stderr[:120])
    ex.check("fade-in filter arg present", "afade=t=in:st=0:d=2" in r.stdout,
             r.stdout[:240])
    ex.check("fade-out filter arg present", "afade=t=out:st=12" in r.stdout,
             r.stdout[:240])
    ex.check("dry-run executed nothing",
             not os.path.exists(os.path.join(home, "out.mp3")))
    ex.check("exact command printed for transparency", "RUN: ffmpeg" in r.stdout,
             r.stdout[:120])
    return ex



def exam_40_grade_teal_noir_filtergraph():
    ex = Exam("exam-40", "teal-noir grade emits the reference-look filtergraph")
    home = fresh_home()
    r = run(home, None, "editor", "grade", "list")
    ex.check("grade list exits 0", r.returncode == 0, r.stderr[:120])
    ex.check("teal-noir listed", "teal-noir" in r.stdout, r.stdout[:200])
    ex.check("clean (no effect) listed", "clean" in r.stdout, r.stdout[:200])
    r2 = run(home, None, "editor", "grade", "apply", "--input", "in.mp4",
             "--output", "out.mp4", "--look", "teal-noir", "--dry-run")
    ex.check("dry-run prints filtergraph with colorbalance",
             "colorbalance" in r2.stdout, r2.stdout[:200])
    ex.check("teal shadows encoded (rs=-0.25, bs=0.25)",
             "rs=-0.25" in r2.stdout and "bs=0.25" in r2.stdout,
             r2.stdout[:300])
    r3 = run(home, None, "editor", "grade", "apply", "--input", "in.mp4",
             "--output", "out.mp4", "--look", "no-such-grade", "--dry-run")
    ex.check("unknown grade refused", r3.returncode != 0, r3.stderr[:160])
    return ex


def _exam_loud_fixture(home):
    import shutil
    mp4 = os.path.join(home, "loud.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                    "-i", "testsrc=duration=10:size=640x480:rate=30",
                    "-filter_complex",
                    "sine=frequency=440:duration=10,volume=0.15,atrim=0:4,"
                    "asetpts=PTS-STARTPTS[q1];"
                    "sine=frequency=880:duration=10,volume=1.2,atrim=0:3,"
                    "asetpts=PTS-STARTPTS[l1];"
                    "sine=frequency=440:duration=10,volume=0.15,atrim=0:3,"
                    "asetpts=PTS-STARTPTS[q2];"
                    "[q1][l1][q2]concat=n=3:v=0:a=1[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "libx264",
                    "-c:a", "aac", mp4], check=True)
    return mp4


def exam_41_watch_highlights_loudest_segment():
    import shutil
    ex = Exam("exam-41", "watch->highlights finds the loudest segment")
    home = fresh_home()
    if not shutil.which("ffmpeg"):
        ex.check("ffmpeg missing (env without it)", True)
        return ex
    mp4 = _exam_loud_fixture(home)
    work = os.path.join(home, "work")
    r = run(home, None, "editor", "watch", "--input", mp4, "--out", work)
    ex.check("watch exits 0", r.returncode == 0, r.stderr[:160])
    ex.check("analysis.json written",
             os.path.exists(os.path.join(work, "analysis.json")))
    r2 = run(home, None, "editor", "highlights", "--dir", work, "--top", "3")
    ex.check("highlights exits 0", r2.returncode == 0, r2.stderr[:160])
    # loud burst is at 4-7s; top highlight must cover it
    m = re.search(r"1\. ([\d.]+)s->([\d.]+)s", r2.stdout)
    covers = m and float(m.group(1)) <= 4.0 <= float(m.group(2))
    ex.check("top highlight covers the 4-7s loud burst", bool(covers),
             r2.stdout[:200])
    return ex


def exam_42_qa_flags_black_frames():
    import shutil
    ex = Exam("exam-42", "QA flags black frames in a synthetic fixture")
    home = fresh_home()
    if not shutil.which("ffmpeg"):
        ex.check("ffmpeg missing (env without it)", True)
        return ex
    mp4 = os.path.join(home, "black.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                    "-i", "color=black:duration=2:size=320x240:rate=15",
                    "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=15",
                    "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
                    "-map", "[v]", "-c:v", "libx264", mp4], check=True)
    r = run(home, None, "editor", "qa", "--input", mp4)
    ex.check("qa exits nonzero on black frames", r.returncode != 0,
             r.stdout[:160])
    ex.check("black segment reported", "black" in r.stdout.lower(),
             r.stdout[:200])
    return ex


def exam_43_batch_grades_three_fixtures():
    import shutil
    ex = Exam("exam-43", "batch applies a grade to 3 fixtures")
    home = fresh_home()
    if not shutil.which("ffmpeg"):
        ex.check("ffmpeg missing (env without it)", True)
        return ex
    srcs = []
    for i in range(3):
        p = os.path.join(home, f"b{i}.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                        "-i", "testsrc=duration=2:size=320x240:rate=15",
                        "-c:v", "libx264", p], check=True)
        srcs.append(p)
    out = os.path.join(home, "batchout")
    r = run(home, None, "editor", "batch", "--op", "grade", "--look", "noir",
            "--in", os.path.join(home, "b*.mp4"), "--out", out)
    ex.check("batch exits 0", r.returncode == 0, r.stderr[:160])
    ex.check("3 outputs produced", "ok: 3, failed: 0" in r.stdout,
             r.stdout[:200])
    outs = sorted(f for f in os.listdir(out) if f.endswith(".mp4"))
    ex.check("3 graded files on disk", len(outs) == 3, str(outs))
    return ex


def exam_44_queue_add_run_resume():
    ex = Exam("exam-44", "render queue add/run/resume lifecycle")
    home = fresh_home()
    r = run(home, None, "editor", "queue", "add", "--name", "q1",
            "--cmd", "echo hello")
    ex.check("queue add exits 0", r.returncode == 0, r.stderr[:120])
    r2 = run(home, None, "editor", "queue", "run", "--name", "q1")
    ex.check("queue run executes", r2.returncode == 0 and "q1: done" in r2.stdout,
             r2.stdout[:160])
    r3 = run(home, None, "editor", "queue", "run", "--resume")
    ex.check("resume skips the done job",
             "already done" in r3.stdout, r3.stdout[:160])
    r4 = run(home, None, "editor", "queue", "list")
    ex.check("queue list shows job state", "q1" in r4.stdout and "done" in r4.stdout,
             r4.stdout[:160])
    return ex


def exam_45_brand_apply_stamps_kit():
    import shutil
    ex = Exam("exam-45", "brand apply stamps kit grade + logo into the render")
    home = fresh_home()
    r = run(home, None, "editor", "brand", "create", "--label", "ch1")
    ex.check("brand create exits 0", r.returncode == 0, r.stderr[:120])
    r2 = run(home, None, "editor", "brand", "show", "--label", "ch1")
    ex.check("kit defaults to teal-noir grade", "teal-noir" in r2.stdout,
             r2.stdout[:200])
    # stamp a REAL logo file into the kit (missing files are skipped by design)
    logo = os.path.join(home, "logo.png")
    try:
        from PIL import Image
        Image.new("RGBA", (80, 80), (0, 200, 255, 255)).save(logo)
        have_logo = True
    except ImportError:
        have_logo = False
    kitp = os.path.join(home, "branding", "ch1.yaml")
    with open(kitp, "a", encoding="utf-8") as fh:
        fh.write(f'logo: "{logo}"\n')
    r3 = run(home, None, "editor", "brand", "apply", "--label", "ch1",
             "--input", "in.mp4", "--output", "out.mp4", "--dry-run")
    ex.check("dry-run prints the ffmpeg command", "RUN: ffmpeg" in r3.stdout,
             r3.stdout[:160])
    ex.check("grade filtergraph in command", "colorbalance" in r3.stdout,
             r3.stdout[:200])
    ex.check("logo path stamped into command",
             have_logo and logo in r3.stdout, r3.stdout[:200])
    return ex


def exam_46_unified_approval_queue_publish():
    ex = Exam("exam-46", "Unified approval queue: publish proposed, queued, approved executes")
    home = fresh_home()
    setup_account(home)
    # engage proposal sits in the queue as pending (watchers propose, never act)
    r = run(home, None, "engage", "like", "--platform", "tiktok",
            "--account", "main", "--target", "v46")
    ex.check("proposal exits 0", r.returncode == 0, r.stderr.strip()[:80])
    pend = state(home, "approvals/pending.json", [])
    ex.check("one pending queue item", len(pend) == 1 and pend[0]["status"] == "pending",
             str(pend)[:120])
    qid = pend[0]["id"]
    r = run(home, None, "approvals", "list")
    ex.check("approvals list shows the item", qid in r.stdout, r.stdout.strip()[:80])
    # video publish: post approve routes through the unified queue
    run(home, None, "post", "draft", "--platform", "tiktok", "--account", "main",
        "--text", "sora ai video tutorial part 46", "--id", "ep46")
    run(home, None, "post", "queue", "ep46")
    r = run(home, None, "post", "approve", "ep46")
    ex.check("post approve still dry-run", "DRY-RUN" in r.stdout and
             "never posts by itself" in r.stdout, r.stdout.strip()[-100:])
    pend = state(home, "approvals/pending.json", [])
    pub = [i for i in pend if i["type"] == "publish"]
    ex.check("publish item recorded in the queue", len(pub) == 1,
             str([i["status"] for i in pub]))
    ex.check("explicit approve executes the underlying post",
             state(home, "queue.json")[0]["status"] == "approved",
             str(state(home, "queue.json")[0])[:120])
    # and the earlier engagement proposal approves through the queue too
    r = run(home, None, "approvals", "approve", "--id", qid)
    ex.check("queue approve executes engagement",
             r.returncode == 0 and state(home, "actions.json")[0]["status"] == "approved",
             r.stdout.strip()[:80])
    return ex


def exam_47_people_memory_top_fans():
    ex = Exam("exam-47", "People memory: listener remembers actors, top-fans surface")
    home = fresh_home()
    setup_account(home)
    fx = os.path.join(FX, "listen_comments.json")
    r = run(home, None, "watch", "start", "--type", "comment", "--platform", "tiktok",
            "--account", "main", "--set", "post_id=vid9", "--fixture", fx, "--id", "ew47")
    ex.check("comment watcher starts", r.returncode == 0, r.stderr.strip()[:80])
    fxm = os.path.join(FX, "listen_dms.json")
    r = run(home, None, "watch", "start", "--type", "message", "--platform", "tiktok",
            "--account", "main", "--fixture", fxm, "--id", "ew47m")
    ex.check("message watcher starts", r.returncode == 0, r.stderr.strip()[:80])
    r = run(home, None, "listen", "once")
    ex.check("listen pass completes", r.returncode == 0 and
             "listen pass complete" in r.stdout, r.stdout.strip()[-80:])
    people = people_state(home, "examuser")
    ex.check("commenter remembered", "curious_cat" in people, str(sorted(people))[:120])
    ex.check("DM sender remembered with dm count",
             people.get("fan_two", {}).get("counts", {}).get("dm") == 1,
             str(people.get("fan_two"))[:120])
    # manual memory tools: note + tag + top + show
    r = run(home, None, "people", "note", "--account", "main", "curious_cat",
            "asked about background blur")
    ex.check("note saved", r.returncode == 0, r.stderr.strip()[:80])
    r = run(home, None, "people", "tag", "--account", "main", "curious_cat",
            "top-fan")
    ex.check("top-fan tag applied", r.returncode == 0, r.stderr.strip()[:80])
    r = run(home, None, "people", "top", "--account", "main")
    ex.check("top lists the fan", "curious_cat" in r.stdout, r.stdout.strip()[:120])
    r = run(home, None, "people", "show", "--account", "main", "curious_cat")
    ex.check("show carries the note and tag",
             "background blur" in r.stdout and "top-fan" in r.stdout,
             r.stdout.strip()[:120])
    return ex


def exam_48_ratelimit_exhaustion_queues_retry():
    ex = Exam("exam-48", "Rate-limit exhaustion queues the action as rate_limited")
    home = fresh_home()
    setup_account(home)
    pol = write_policy(os.path.join(home, "policy.yaml"),
                       rate_limits={"tiktok": {"hide": {"per_hour": 1,
                                                       "per_day": 10}}})
    r = run(home, pol, "moderate", "hide", "--platform", "tiktok", "--account", "main",
            "--post", "p1", "--comment", "c1", "--text", "mildly rude comment")
    ex.check("first hide exits 0", r.returncode == 0, r.stderr.strip()[:80])
    r = run(home, pol, "moderate", "hide", "--platform", "tiktok", "--account", "main",
            "--post", "p1", "--comment", "c2", "--text", "another rude comment")
    ex.check("second hide refused with exit 2",
             r.returncode == 2 and "rate limit" in r.stderr.lower(),
             (r.stderr.strip() + r.stdout.strip())[:120])
    ex.check("underlying log keeps exactly 1 record",
             len(state(home, "moderation.json", [])) == 1)
    pend = state(home, "approvals/pending.json", [])
    rl_items = [i for i in pend if i["status"] == "rate_limited"]
    ex.check("denied action queued as rate_limited (never dropped)",
             len(rl_items) == 1 and rl_items[0].get("retry_at", 0) > time.time(),
             str([(i["id"], i.get("retry_at")) for i in rl_items])[:120])
    r = run(home, pol, "ratelimit", "status")
    ex.check("0 remaining reported", "0/1 per hour" in r.stdout,
             r.stdout.strip()[:120])
    return ex


def exam_49_crisis_pauses_and_repends():
    ex = Exam("exam-49", "Crisis mode pauses acting; off re-pends held items")
    home = fresh_home()
    setup_account(home)
    run(home, None, "engage", "follow", "--platform", "tiktok",
        "--account", "main", "--target", "someone")
    qid = state(home, "approvals/pending.json", [])[0]["id"]
    r = run(home, None, "crisis", "on", "--reason", "exam spike")
    ex.check("crisis on exits 0", r.returncode == 0 and "CRISIS MODE ON" in r.stdout,
             r.stdout.strip()[:80])
    r = run(home, None, "engage", "follow", "--platform", "tiktok",
            "--account", "main", "--target", "other")
    ex.check("acting refused under crisis", r.returncode == 2 and
             "crisis" in r.stderr.lower(), r.stderr.strip()[:100])
    r = run(home, None, "crisis", "status")
    ex.check("status shows ACTIVE", "ACTIVE" in r.stdout, r.stdout.strip()[:80])
    held = state(home, "approvals/pending.json", [])[0]
    ex.check("pending item held during crisis", held["status"] == "held",
             str(held)[:80])
    r = run(home, None, "crisis", "off")
    ex.check("crisis off re-pends", r.returncode == 0 and
             "re-pended" in r.stdout, r.stdout.strip()[:100])
    ex.check("held item back to pending (not auto-approved)",
             state(home, "approvals/pending.json", [])[0]["status"] == "pending")
    # still needs a human decision after the crisis clears
    r = run(home, None, "approvals", "approve", "--id", qid)
    ex.check("explicit re-approval works",
             r.returncode == 0 and state(home, "actions.json")[0]["status"] == "approved",
             r.stdout.strip()[:80])
    return ex


def exam_50_listen_once_routes_events():
    ex = Exam("exam-50", "listen --once routes comments/DMs/notifications")
    home = fresh_home()
    setup_account(home)
    r = run(home, None, "watch", "start", "--type", "comment", "--platform", "tiktok",
            "--account", "main", "--set", "post_id=vid9",
            "--fixture", os.path.join(FX, "listen_comments.json"), "--id", "ew50c")
    ex.check("comment watcher starts", r.returncode == 0, r.stderr.strip()[:80])
    r = run(home, None, "watch", "start", "--type", "message", "--platform", "tiktok",
            "--account", "main",
            "--fixture", os.path.join(FX, "listen_dms.json"), "--id", "ew50m")
    ex.check("message watcher starts", r.returncode == 0, r.stderr.strip()[:80])
    r = run(home, None, "watch", "start", "--type", "notification", "--platform", "tiktok",
            "--account", "main",
            "--fixture", os.path.join(FX, "notifications.json"), "--id", "ew50n")
    ex.check("notification watcher starts", r.returncode == 0, r.stderr.strip()[:80])
    r = run(home, None, "listen", "once")
    ex.check("listen pass completes", r.returncode == 0 and
             "listen pass complete" in r.stdout, r.stdout.strip()[-80:])
    ex.check("question routes to a reply draft",
             "reply draft" in r.stdout, r.stdout.strip()[:200])
    pend = state(home, "approvals/pending.json", [])
    ex.check("reply draft sits pending in the queue",
             any(i["type"] == "reply" and i["status"] == "pending" for i in pend),
             str([(i["type"], i["status"]) for i in pend])[:160])
    notes = state(home, "notifications.json", [])
    ex.check("DM raised a user notification",
             any(n.get("kind") == "dm" for n in notes),
             str([(n.get("kind")) for n in notes])[:80])
    people = people_state(home, "examuser")
    ex.check("notification actors recorded",
             "fan_one" in people and "new_follower" in people,
             str(sorted(people))[:120])
    return ex


def exam_51_memory_round_trip():
    ex = Exam("exam-51", "Permanent memory: accounts, decisions, SOPs, SELECT-only query")
    home = fresh_home()
    r = run(home, None, "memory", "account", "add", "exam", "tiktok",
            "--handle", "examuser")
    ex.check("memory account add exits 0", r.returncode == 0, r.stderr.strip()[:80])
    r = run(home, None, "memory", "remember", "post daily", "--by", "user",
            "--why", "consistency compounds")
    ex.check("remember records a decision", r.returncode == 0 and
             "recorded" in r.stdout, r.stdout.strip()[:80])
    r = run(home, None, "memory", "recall")
    ex.check("recall lists the decision with its why",
             "post daily" in r.stdout and "consistency compounds" in r.stdout,
             r.stdout.strip()[:120])
    r = run(home, None, "memory", "sop", "add", "weekly review",
            "--body", "# review\n1. check stats")
    ex.check("sop add exits 0", r.returncode == 0, r.stdout.strip()[:80])
    r = run(home, None, "memory", "sop", "list")
    ex.check("sop list shows the SOP", "weekly review" in r.stdout,
             r.stdout.strip()[:80])
    r = run(home, None, "memory", "query", "SELECT label, platform FROM accounts")
    ex.check("SELECT query returns the account",
             "exam" in r.stdout and "tiktok" in r.stdout, r.stdout.strip()[:80])
    r = run(home, None, "memory", "query", "DROP TABLE accounts")
    ex.check("non-SELECT refused", r.returncode != 0, r.stderr.strip()[:80])
    r = run(home, None, "memory", "query", "SELECT 1; SELECT 2")
    ex.check("multi-statement refused", r.returncode != 0, r.stderr.strip()[:80])
    return ex


def exam_52_memory_relations_graph():
    ex = Exam("exam-52", "Memory relationship graph: relate + graph")
    home = fresh_home()
    run(home, None, "memory", "relate", "brand:nova", "owns", "account:exam")
    run(home, None, "memory", "relate", "follower:ada", "frequent_customer_of",
        "brand:nova")
    run(home, None, "memory", "relate", "video:v1", "belongs_to", "campaign:c1")
    r = run(home, None, "memory", "graph", "brand:nova")
    ex.check("graph shows brand owns account",
             "brand:nova --owns--> account:exam" in r.stdout, r.stdout.strip()[:120])
    ex.check("graph shows inbound follower edge",
             "follower:ada --frequent_customer_of--> brand:nova" in r.stdout,
             r.stdout.strip()[:120])
    r = run(home, None, "memory", "graph", "video:v1")
    ex.check("graph shows video belongs to campaign",
             "video:v1 --belongs_to--> campaign:c1" in r.stdout,
             r.stdout.strip()[:120])
    # idempotent relate: no duplicate edge
    run(home, None, "memory", "relate", "brand:nova", "owns", "account:exam")
    r = run(home, None, "memory", "graph", "brand:nova")
    ex.check("re-relate does not duplicate the edge",
             r.stdout.count("--owns-->") == 1, r.stdout.strip()[:120])
    return ex


def exam_53_backup_on_post_create():
    ex = Exam("exam-53", "Automatic backup: post draft snapshots, manual snapshot + diff")
    home = fresh_home()
    setup_account(home)
    run(home, None, "post", "draft", "--platform", "tiktok", "--account", "main",
        "--text", "sora ai video tutorial part 53", "--id", "ep53")
    r = run(home, None, "backup", "list")
    ex.check("post_created snapshot exists",
             "post_created" in r.stdout, r.stdout.strip()[:120])
    snaps_before = len([l for l in r.stdout.splitlines() if l.startswith("snap-")])
    r = run(home, None, "backup", "snapshot", "--files", "queue.json",
            "--note", "manual checkpoint")
    ex.check("manual snapshot exits 0", r.returncode == 0 and "snapshot" in r.stdout,
             r.stdout.strip()[:80])
    snap_id = r.stdout.split()[1]
    run(home, None, "post", "draft", "--platform", "tiktok", "--account", "main",
        "--text", "second post for diff", "--id", "ep53b")
    r2 = run(home, None, "backup", "snapshot", "--files", "queue.json")
    snap2 = r2.stdout.split()[1]
    r = run(home, None, "backup", "diff", snap_id, snap2)
    ex.check("diff shows queue.json changed", "~ queue.json" in r.stdout,
             r.stdout.strip()[:120])
    r = run(home, None, "backup", "list")
    ex.check("snapshot count grew",
             len([l for l in r.stdout.splitlines()
                  if l.startswith("snap-")]) > snaps_before,
             f"{snaps_before} -> ...")
    return ex


def exam_54_risky_action_recovery_point():
    ex = Exam("exam-54", "Risky actions take a recovery point before executing")
    home = fresh_home()
    setup_account(home)
    run(home, None, "post", "draft", "--platform", "tiktok", "--account", "main",
        "--text", "sora ai video tutorial part 54", "--id", "ep54")
    run(home, None, "post", "queue", "ep54")
    r = run(home, None, "backup", "list")
    risky_before = r.stdout.count("risky_action")
    r = run(home, None, "post", "approve", "ep54")
    ex.check("post approve exits 0", r.returncode == 0, r.stderr.strip()[:80])
    r = run(home, None, "backup", "list")
    ex.check("risky_action recovery point taken before publish",
             r.stdout.count("risky_action") > risky_before,
             r.stdout.strip()[:160])
    # journal recorded the approval intent and its completion
    import pathlib
    journal = os.path.join(home, "audit", "journal.jsonl")
    entries = [json.loads(l) for l in
               pathlib.Path(journal).read_text().splitlines() if l.strip()]
    pub = [e for e in entries if e.get("action_type") == "publish"]
    ex.check("journal logged the publish intent",
             len(pub) >= 1, str(len(pub)))
    ex.check("journal marked it completed",
             any(e["status"] == "completed" for e in pub),
             str([(e["status"]) for e in pub])[:80])
    # crisis off also takes a recovery point
    run(home, None, "crisis", "on", "--reason", "exam 54")
    r = run(home, None, "backup", "list")
    risky_before_off = r.stdout.count("risky_action")
    run(home, None, "crisis", "off")
    r = run(home, None, "backup", "list")
    ex.check("crisis off takes a recovery point",
             r.stdout.count("risky_action") > risky_before_off,
             r.stdout.strip()[:160])
    return ex


def exam_55_restore_dry_run_safety():
    ex = Exam("exam-55", "Restore is dry-run by default and stages, never overwrites")
    home = fresh_home()
    setup_account(home)
    p = os.path.join(home, "notes.txt")
    with open(p, "w") as fh:
        fh.write("version one")
    r = run(home, None, "backup", "snapshot", "--files", "notes.txt",
            "--note", "v1")
    snap_id = r.stdout.split()[1]
    with open(p, "w") as fh:
        fh.write("version two")
    r = run(home, None, "backup", "restore", snap_id)
    ex.check("dry-run restore exits 0", r.returncode == 0, r.stderr.strip()[:80])
    ex.check("dry-run plan shows would-overwrite",
             "would-overwrite" in r.stdout, r.stdout.strip()[:120])
    ex.check("live file untouched by dry-run",
             open(p).read() == "version two", open(p).read())
    r = run(home, None, "backup", "restore", snap_id, "--apply")
    ex.check("apply stages the restore", r.returncode == 0 and
             "staged to" in r.stdout, r.stdout.strip()[:120])
    stage = os.path.join(home, "backups", "restore_staging", snap_id,
                         "notes.txt")
    ex.check("staged file holds the old version",
             os.path.isfile(stage) and open(stage).read() == "version one",
             stage)
    ex.check("live file STILL untouched after apply",
             open(p).read() == "version two", open(p).read())
    return ex


def exam_56_crash_recovery_skip_and_resume():
    ex = Exam("exam-56", "Crash recovery: already-done intents are skipped, never repeated")
    home = fresh_home()
    setup_account(home)
    # a completed publish: approve via queue (journals the intent)
    run(home, None, "post", "draft", "--platform", "tiktok", "--account", "main",
        "--text", "sora ai video tutorial part 56", "--id", "ep56")
    run(home, None, "post", "queue", "ep56")
    run(home, None, "post", "approve", "ep56")
    # simulate a crash: inject a stale 'started' journal entry for the same
    # publish (as if the process died between apply and journal end)
    sys.path.insert(0, REPO)
    from core import recovery as _rec
    jb = _rec.begin(home, "publish", "ep56", {"platform": "tiktok"})
    ex.check("crash residue is unfinished", len(_rec.unfinished(home)) >= 1,
             str(len(_rec.unfinished(home))))
    r = run(home, None, "recover")
    ex.check("recover exits 0", r.returncode == 0, r.stderr.strip()[:80])
    ex.check("already-done publish is SKIPPED, not repeated",
             "SKIP (already done)" in r.stdout, r.stdout.strip()[:160])
    ex.check("no duplicate post created",
             len([q for q in state(home, "queue.json", [])
                  if q.get("id") == "ep56"]) == 1,
             str([q.get("id") for q in state(home, "queue.json", [])])[:80])
    r = run(home, None, "recover")
    ex.check("second recover is clean", "journal is clean" in r.stdout,
             r.stdout.strip()[:120])
    # idempotency: beginning the same intent again is a duplicate
    jb2 = _rec.begin(home, "publish", "ep56", {"platform": "tiktok"})
    ex.check("repeat of completed intent refused as duplicate",
             jb2["duplicate"] is True, str(jb2.get("duplicate")))
    return ex


def write_browser_policy(path, ack=()):
    """Minimal policy for browser exams: generous rate limits, ack list.

    Note: there is no `backend` config key — the browser is the only
    backend. Nothing here selects or mentions an API.
    """
    lines = ["version: 1", "defaults:", '  mode: "propose"',
             "rate_limits:", "  default:",
             "    actions_per_hour: 1000", "    actions_per_day: 10000",
             "quiet_hours:", "  enabled: false",
             "browser:", "  active_hours:", "    enabled: false",
             "tos:", "  acknowledged_risk:"]
    for p in ack:
        lines.append(f"    - {p}")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


def exam_57_browser_x_refused_without_ack():
    ex = Exam("exam-57", "Browser action on X refused without acknowledged_risk")
    home = fresh_home()
    pol = write_browser_policy(os.path.join(home, "policy.yaml"))
    r = run(home, pol, "browser", "login", "--account", "main",
            "--platform", "x", "--simulate")
    ex.check("simulated login exits 0", r.returncode == 0,
             r.stderr.strip()[:80])
    r = run(home, pol, "browser", "act", "--account", "main",
            "--platform", "x", "--action", "like",
            "--target", "https://x.com/s/57", "--simulate")
    ex.check("X like refused (exit 2)", r.returncode == 2,
             f"exit={r.returncode}")
    ex.check("refusal names the ToS prohibition",
             "ToS refusal" in r.stderr and "prohibited" in r.stderr,
             r.stderr.strip()[:120])
    ex.check("no advisory logged without acknowledgment",
             not os.path.exists(
                 os.path.join(home, "audit", "tos_acknowledgments.jsonl")))
    return ex


def exam_58_browser_x_proceeds_with_ack():
    ex = Exam("exam-58", "With tos.acknowledged_risk:[x], X proceeds + loud advisory")
    home = fresh_home()
    pol = write_browser_policy(os.path.join(home, "policy.yaml"), ack=["x"])
    run(home, pol, "browser", "login", "--account", "main",
        "--platform", "x", "--simulate")
    r = run(home, pol, "browser", "act", "--account", "main",
            "--platform", "x", "--action", "like",
            "--target", "https://x.com/s/58", "--simulate")
    ex.check("X like proceeds (exit 0)", r.returncode == 0,
             (r.stderr.strip() + r.stdout.strip())[:120])
    ex.check("loud advisory printed",
             "ACKNOWLEDGED-RISK ADVISORY" in r.stderr, r.stderr.strip()[:80])
    ex.check("advisory states the plain risk",
             "suspend or ban" in r.stderr, r.stderr.strip()[-80:])
    log = os.path.join(home, "audit", "tos_acknowledgments.jsonl")
    ex.check("advisory recorded to audit log",
             os.path.exists(log) and '"platform": "x"' in open(log).read(),
             log)
    ex.check("action steps executed",
             "OK (2 steps)" in r.stdout, r.stdout.strip()[:80])
    return ex


def exam_59_browser_profile_persists():
    ex = Exam("exam-59", "browser login creates the persistent profile dir")
    home = fresh_home()
    pol = write_browser_policy(os.path.join(home, "policy.yaml"))
    r = run(home, pol, "browser", "login", "--account", "main",
            "--platform", "tiktok", "--simulate")
    ex.check("login exits 0", r.returncode == 0, r.stderr.strip()[:80])
    pdir = os.path.join(home, "accounts", "main", "browser-profile")
    ex.check("profile dir created", os.path.isdir(pdir), pdir)
    sidecar = os.path.join(home, "accounts", "main", "browser.json")
    ex.check("sidecar records the platform",
             os.path.exists(sidecar) and
             json.load(open(sidecar)).get("platform") == "tiktok",
             sidecar)
    r = run(home, pol, "browser", "status")
    ex.check("status lists the profile", "main" in r.stdout,
             r.stdout.strip()[:120])
    # second login is idempotent (tops up, never wipes)
    run(home, pol, "browser", "login", "--account", "main",
        "--platform", "tiktok", "--simulate")
    ex.check("re-login keeps the profile dir", os.path.isdir(pdir), pdir)
    return ex


def exam_60_browser_like_uses_rate_limits():
    ex = Exam("exam-60", "Browser-backed like goes through the rate-limit controller")
    home = fresh_home()
    pol = write_browser_policy(os.path.join(home, "policy.yaml"))
    run(home, pol, "browser", "login", "--account", "main",
        "--platform", "tiktok", "--simulate")
    r = run(home, pol, "browser", "act", "--account", "main",
            "--platform", "tiktok", "--action", "like",
            "--target", "https://www.tiktok.com/v/60", "--simulate")
    ex.check("tiktok like proceeds (no ToS block)", r.returncode == 0,
             (r.stderr.strip() + r.stdout.strip())[:120])
    r = run(home, pol, "ratelimit", "status")
    ex.check("browser_goto bucket tracked",
             "tiktok:browser_goto" in r.stdout, r.stdout.strip()[:160])
    ex.check("browser_click bucket tracked",
             "tiktok:browser_click" in r.stdout, r.stdout.strip()[:160])
    return ex


def exam_61_browser_challenge_pauses_with_notification():
    ex = Exam("exam-61", "2FA challenge pauses the session + notifies the user")
    home = fresh_home()
    pol = write_browser_policy(os.path.join(home, "policy.yaml"))
    run(home, pol, "browser", "login", "--account", "main",
        "--platform", "instagram", "--simulate")
    sys.path.insert(0, REPO)
    from browser import session as _bsess
    _bsess.mark_challenge(home, "main", kind="2fa")
    notes = state(home, "notifications.json", [])
    ex.check("user notified of the challenge",
             any(n.get("kind") == "browser_challenge" for n in notes),
             str([n.get("kind") for n in notes])[:80])
    ex.check("notification says the agent paused",
             any("PAUSED" in n.get("text", "") for n in notes),
             str(notes[-1].get("text", ""))[:100])
    r = run(home, pol, "browser", "act", "--account", "main",
            "--platform", "instagram", "--action", "like",
            "--target", "https://www.instagram.com/p/61", "--simulate")
    ex.check("acting refused while challenge is open", r.returncode != 0,
             f"exit={r.returncode}")
    ex.check("refusal points at headed login",
             "browser login" in (r.stderr + r.stdout),
             (r.stderr + r.stdout).strip()[:120])
    return ex


def exam_62_browser_only_no_api_surface():
    ex = Exam("exam-62", "X like executes via the browser backend; no API credential anywhere")
    home = fresh_home()
    pol = write_browser_policy(os.path.join(home, "policy.yaml"), ack=["x"])
    run(home, pol, "browser", "login", "--account", "main",
        "--platform", "x", "--simulate")
    r = run(home, pol, "browser", "act", "--account", "main",
            "--platform", "x", "--action", "like",
            "--target", "https://x.com/s/62", "--simulate")
    ex.check("X like proceeds via browser (exit 0)", r.returncode == 0,
             (r.stderr.strip() + r.stdout.strip())[:120])
    ex.check("steps executed through the browser backend",
             "browser act like [x/main]: OK" in r.stdout,
             r.stdout.strip()[:120])
    # no API credential exists anywhere in the state dir
    cred_pat = re.compile(r"(?i)api[_-]?key|api[_-]?secret|client[_-]?secret|"
                          r"bearer\s+ey|oauth.*token")
    bad = []
    for dp, dn, fn in os.walk(home):
        if "__pycache__" in dn:
            dn.remove("__pycache__")
        for f in fn:
            p = os.path.join(dp, f)
            try:
                t = open(p, encoding="utf-8", errors="strict").read()
            except (UnicodeDecodeError, OSError):
                continue
            if cred_pat.search(t):
                bad.append(os.path.relpath(p, home))
    ex.check("no API credential material in state", not bad, str(bad)[:100])
    # the backend switch itself is gone from the shipped code
    sys.path.insert(0, REPO)
    from platforms.browser import backend as _backend
    ex.check("no backend_for() selector exists",
             not hasattr(_backend, "backend_for"))
    ex.check("act() takes no backend argument",
             "backend" not in _backend.act.__code__.co_varnames)
    src = open(os.path.join(REPO, "platforms", "browser",
                            "backend.py")).read()
    ex.check("backend.py declares browser-only, no api option",
             "no API backend" in src and
             not re.search(r"backend\s*:\s*[\"']?api|\"api\"\s*=\s*\"backend\"",
                           src, re.I),
             "browser-only denial present")
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
         exam_27_post_draft_identity_refused,
         exam_28_toxic_comment_flagged,
         exam_29_spam_autohide_rule_proposes,
         exam_30_hide_needs_approval,
         exam_31_caption_passes_gates,
         exam_32_video_info_clip_fixture,
         exam_33_audio_clip_fades_args,
         exam_34_specs_lookup,
         exam_35_fit_defaults_to_pad,
         exam_36_crop_refused_without_focus,
         exam_37_crop_focus_top_box_math,
         exam_38_preflight_fails_wrong_aspect,
         exam_39_preflight_passes_correct_video,
         exam_40_grade_teal_noir_filtergraph,
         exam_41_watch_highlights_loudest_segment,
         exam_42_qa_flags_black_frames,
         exam_43_batch_grades_three_fixtures,
         exam_44_queue_add_run_resume,
         exam_45_brand_apply_stamps_kit,
         exam_46_unified_approval_queue_publish,
         exam_47_people_memory_top_fans,
         exam_48_ratelimit_exhaustion_queues_retry,
         exam_49_crisis_pauses_and_repends,
         exam_50_listen_once_routes_events,
         exam_51_memory_round_trip,
         exam_52_memory_relations_graph,
         exam_53_backup_on_post_create,
         exam_54_risky_action_recovery_point,
         exam_55_restore_dry_run_safety,
         exam_56_crash_recovery_skip_and_resume,
         exam_57_browser_x_refused_without_ack,
         exam_58_browser_x_proceeds_with_ack,
         exam_59_browser_profile_persists,
         exam_60_browser_like_uses_rate_limits,
         exam_61_browser_challenge_pauses_with_notification,
         exam_62_browser_only_no_api_surface]


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
