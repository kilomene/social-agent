"""Crisis mode state machine (stdlib only)."""

import json
import os
from datetime import datetime, timezone

STATE = "crisis.json"

# Approval-queue item types that ACT on platforms and must freeze in crisis.
ACTING_TYPES = {"like", "comment", "follow", "retweet", "hide", "hide_spam",
                "post", "post_video", "publish", "dm", "reply"}


class CrisisActive(Exception):
    """Raised by the acting guard while crisis mode is on."""


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _path(home):
    return os.path.join(home, STATE)


def get(home):
    p = _path(home)
    if not os.path.exists(p):
        return {"active": False, "reason": "", "started_at": None, "held": []}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _save(home, state):
    tmp = _path(home) + ".tmp"
    os.makedirs(home, exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)
    os.replace(tmp, _path(home))


def is_active(home):
    return bool(get(home).get("active"))


def check(home):
    """Raise CrisisActive if crisis mode is on (called by the acting guard)."""
    st = get(home)
    if st.get("active"):
        raise CrisisActive(
            f"crisis mode ACTIVE since {st.get('started_at')}: "
            f"{st.get('reason') or 'no reason given'} — all acting "
            f"operations are paused")


def activate(home, reason="", hold_fn=None):
    """Turn crisis mode on. hold_fn() -> list of held item ids (optional)."""
    held = hold_fn() if hold_fn else []
    st = {"active": True, "reason": reason, "started_at": utcnow(),
          "held": held}
    _save(home, st)
    return st


def deactivate(home, release_fn=None):
    """Turn crisis mode off. Never auto-resumes: only an explicit
    `crisis off` (or equivalent API call) clears it. release_fn(held_ids)
    re-pends held items; returns (state, released_ids)."""
    st = get(home)
    held = list(st.get("held") or [])
    released = release_fn(held) if release_fn else held
    st = {"active": False, "reason": "", "started_at": None, "held": []}
    _save(home, st)
    return st, released
