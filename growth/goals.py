"""Follower/milestone goal tracking (pure stdlib).

Goals live in <home>/growth_goals.json. Progress is read from activity
watcher state (watchers/<id>.json -> state.last_snapshot.followers) plus any
user-supplied numbers passed at audit time. Milestone crossings (25/50/75/100%)
are appended to events.jsonl so they show up in analytics.
"""

import json
import os
import time
from datetime import datetime, timezone

GOALS_FILE = "growth_goals.json"
EVENTS_LOG = "events.jsonl"

MILESTONES = (25, 50, 75, 100)


def _goals_path(home):
    return os.path.join(home, GOALS_FILE)


def load_goals(home):
    p = _goals_path(home)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _save_goals(home, goals):
    os.makedirs(home, exist_ok=True)
    p = _goals_path(home)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(goals, fh, indent=2)
    os.replace(tmp, p)


def set_goal(home, platform, account, target_followers, deadline, label="",
             starting_followers=0):
    """Create a goal. Returns the goal dict."""
    goals = load_goals(home)
    gid = f"g-{int(time.time()) % 16**6:06x}"
    goal = {
        "id": gid,
        "platform": platform,
        "account": account,
        "target_followers": int(target_followers),
        "deadline": deadline,
        "label": label or f"{target_followers} followers by {deadline}",
        "starting_followers": int(starting_followers),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "milestones_hit": [],
    }
    goals.append(goal)
    _save_goals(home, goals)
    return goal


def current_followers(home, platform, account):
    """Best-effort follower count from activity watcher snapshots."""
    wdir = os.path.join(home, "watchers")
    best = None
    if not os.path.isdir(wdir):
        return None
    for fn in sorted(os.listdir(wdir)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(wdir, fn), encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        st = data.get("state", {})
        snap = st.get("last_snapshot", {})
        if ("followers" in snap and
                str(data.get("account", "")).lower() == account.lower() and
                str(data.get("platform", "")).lower() == platform.lower()):
            ts = st.get("last_poll", "")
            if best is None or ts > best[0]:
                best = (ts, snap["followers"])
    return best[1] if best else None


def progress(home, goal, followers=None):
    """Compute progress dict for a goal. followers overrides watcher state."""
    if followers is None:
        followers = current_followers(home, goal["platform"], goal["account"])
    start = goal.get("starting_followers", 0)
    target = goal["target_followers"]
    span = max(target - start, 1)
    cur = start if followers is None else followers
    pct = max(0.0, min(100.0, (cur - start) / span * 100.0))
    remaining = max(target - cur, 0)
    return {
        "goal_id": goal["id"],
        "label": goal["label"],
        "current": cur,
        "target": target,
        "percent": round(pct, 1),
        "remaining": remaining,
        "deadline": goal["deadline"],
        "source": "watcher" if followers is not None else "none",
    }


def check_milestones(home, goal, prog):
    """Append milestone events for newly crossed thresholds. Returns new hits."""
    goals = load_goals(home)
    rec = next((g for g in goals if g["id"] == goal["id"]), None)
    if rec is None:
        return []
    hit = [m for m in MILESTONES
           if prog["percent"] >= m and m not in rec.get("milestones_hit", [])]
    if not hit:
        return []
    rec.setdefault("milestones_hit", []).extend(hit)
    _save_goals(home, goals)
    os.makedirs(home, exist_ok=True)
    with open(os.path.join(home, EVENTS_LOG), "a", encoding="utf-8") as fh:
        for m in hit:
            fh.write(json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "watcher": "growth-goals",
                "platform": goal["platform"],
                "kind": "growth:milestone",
                "severity": "info",
                "summary": (f"Milestone: {m}% of goal {goal['label']} "
                            f"({prog['current']}/{prog['target']} followers)"),
                "data": {"goal_id": goal["id"], "milestone": m},
            }) + "\n")
    return hit
