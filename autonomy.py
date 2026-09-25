"""Autonomy: explicit, scoped, revocable autonomous mode.

Autonomy is NEVER on by default. The user grants it for exactly one mission:

    social-agent autonomy grant --mission <name> --confirm

In autonomous mode the agent may act WITHOUT per-action approval, but ONLY
inside the mission scope (platforms, allowed actions, topics). Hard blocks
that autonomy can never override:

  * profile changes (display name, username, bio, avatar) — always need an
    explicit `profile approve`, even in autonomous mode
  * DMs — never mission-scoped
  * anything outside the mission's platforms / topics / allowed actions

Grant state lives in $SOCIAL_AGENT_HOME/autonomy.json and is revocable at
any time with `autonomy revoke`.
"""

import json
import os
import time
from datetime import datetime, timezone

import missions

STATE_FILE = "autonomy.json"

# Actions that can never be auto-approved, no matter the mission.
NEVER_AUTO = {"dm", "profile"}


def _home():
    return os.environ.get("SOCIAL_AGENT_HOME", os.path.expanduser("~/.social-agent"))


def _path():
    return os.path.join(_home(), STATE_FILE)


def load_state():
    p = _path()
    if not os.path.exists(p):
        return {"granted": False}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def save_state(data):
    os.makedirs(_home(), exist_ok=True)
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, _path())


def grant(mission_name):
    meta = missions.get_mission(mission_name)
    if meta is None:
        raise ValueError(f"unknown mission {mission_name!r}; see `mission list`")
    errors = missions.validate_mission(meta)
    if errors:
        raise ValueError("mission invalid: " + "; ".join(errors))
    state = {
        "granted": True,
        "mission": meta["name"],
        "granted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "granted_at_ts": time.time(),
        "counters": {},
    }
    save_state(state)
    return meta


def revoke():
    save_state({"granted": False,
                "revoked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})


def active_mission():
    """Return the mission meta if autonomy is currently granted, else None."""
    st = load_state()
    if not st.get("granted"):
        return None
    return missions.get_mission(st.get("mission"))


def check_scope(platform, action, text=""):
    """(allowed, reason). Pure function of the active mission."""
    if action in NEVER_AUTO:
        return False, f"{action} can never be auto-approved (hard rule)"
    mission = active_mission()
    if mission is None:
        return False, "autonomy not granted"
    if platform not in (mission.get("platforms") or []):
        return False, f"platform {platform!r} outside mission scope"
    if action not in (mission.get("allowed_actions") or []):
        return False, f"action {action!r} not allowed by mission"
    topics = mission.get("topics") or []
    if topics and text:
        hay = text.lower()
        if not any(t.lower() in hay for t in topics):
            return False, "content outside mission topics"
    return True, "in mission scope"


def check_mission_limit(action):
    """Enforce per-mission daily counters (posts/likes/follows per day)."""
    st = load_state()
    mission = active_mission()
    if mission is None:
        return
    limits = mission.get("limits") or {}
    key_map = {"post": "posts_per_day", "like": "likes_per_day",
               "follow": "follows_per_day", "comment": "comments_per_day"}
    lkey = key_map.get(action)
    if not lkey or lkey not in limits:
        return
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    counters = st.setdefault("counters", {}).setdefault(day, {})
    used = counters.get(lkey, 0)
    cap = limits[lkey]
    if used >= cap:
        raise RuntimeError(f"mission limit: {lkey} {used}/{cap} used today")
    counters[lkey] = used + 1
    save_state(st)
