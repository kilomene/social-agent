"""Sliding-window rate-limit controller, stdlib only."""

import json
import os
import time

STATE = "ratelimit_buckets.json"
HOUR = 3600
DAY = 86400
MAX_BACKOFF = 86400


def _state_path(home):
    return os.path.join(home, STATE)


def _load(home):
    p = _state_path(home)
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(home, data):
    tmp = _state_path(home) + ".tmp"
    os.makedirs(home, exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, _state_path(home))


def _pick(dicts, new_key, old_key, default):
    """First present key wins, scanning dicts in priority order. Reads the
    new per-action format (per_hour/per_day) and the legacy flat format
    (actions_per_hour/actions_per_day)."""
    for d in dicts:
        if not isinstance(d, dict):
            continue
        if new_key in d:
            return int(d[new_key])
        if old_key in d:
            return int(d[old_key])
    return default


def limits_for(policy, platform, action):
    """Effective (per_hour, per_day) caps for a platform+action.

    Lookup order: action-level dict -> platform section -> default section
    -> built-in default. Both the new per-action format (per_hour/per_day)
    and the legacy flat format (actions_per_hour/actions_per_day) are read.
    """
    rl = (policy or {}).get("rate_limits") or {}
    default = rl.get("default") or {}
    plat = rl.get(platform) or {}
    act = plat.get(action)
    if isinstance(act, dict):
        chain = (act, plat, default)
    else:
        chain = (plat, default)
    return (_pick(chain, "per_hour", "actions_per_hour", 30),
            _pick(chain, "per_day", "actions_per_day", 200))


def _bucket(data, platform, action):
    key = f"{platform}:{action}"
    b = data.get(key)
    if not isinstance(b, dict):
        b = {"hits": [], "denials": 0}
        data[key] = b
    b.setdefault("hits", [])
    b.setdefault("denials", 0)
    return b


def _prune(b, now):
    b["hits"] = [t for t in b["hits"] if now - t < DAY]


def check(home, platform, action, policy, now=None):
    """Return a verdict dict. Never raises.

    allowed=True  -> caller should consume() after the action is created.
    allowed=False -> retry_at is an epoch timestamp; caller must queue the
                     action as rate_limited, never drop it.
    """
    now = time.time() if now is None else now
    per_h, per_d = limits_for(policy, platform, action)
    data = _load(home)
    b = _bucket(data, platform, action)
    _prune(b, now)
    hour_hits = [t for t in b["hits"] if now - t < HOUR]
    remaining_h = max(0, per_h - len(hour_hits))
    remaining_d = max(0, per_d - len(b["hits"]))
    verdict = {
        "allowed": True, "retry_at": None,
        "remaining_hour": remaining_h, "remaining_day": remaining_d,
        "per_hour": per_h, "per_day": per_d,
        "reset_hour_in": 0, "denials": b["denials"],
    }
    if remaining_h <= 0 or remaining_d <= 0:
        window = b["hits"]
        if remaining_h <= 0:
            window = hour_hits
        oldest = min(window) if window else now
        span = HOUR if remaining_h <= 0 else DAY
        base_wait = max(1, int(oldest + span - now))
        # Exponential backoff on consecutive denials (documented).
        wait = min(base_wait * (2 ** min(b["denials"], 4)), MAX_BACKOFF)
        b["denials"] = b["denials"] + 1
        _save(home, data)
        verdict.update({
            "allowed": False, "retry_at": now + wait,
            "reset_hour_in": base_wait,
            "reason": (f"rate limit: {platform}/{action} "
                       f"cap ({per_h}/h, {per_d}/d) reached; "
                       f"retry in ~{wait}s"),
        })
    return verdict


def consume(home, platform, action, now=None):
    """Record one performed (or proposed-and-counted) action."""
    now = time.time() if now is None else now
    data = _load(home)
    b = _bucket(data, platform, action)
    _prune(b, now)
    b["hits"].append(now)
    b["denials"] = 0  # success resets the backoff
    _save(home, data)


def status(home, policy):
    """All buckets with remaining counts (for `ratelimit status`)."""
    data = _load(home)
    now = time.time()
    out = []
    for key, b in sorted(data.items()):
        platform, _, action = key.partition(":")
        per_h, per_d = limits_for(policy, platform, action or "any")
        _prune(b, now)
        hour_hits = [t for t in b["hits"] if now - t < HOUR]
        out.append({
            "bucket": key,
            "per_hour": per_h, "per_day": per_d,
            "remaining_hour": max(0, per_h - len(hour_hits)),
            "remaining_day": max(0, per_d - len(b["hits"])),
            "denials": b.get("denials", 0),
        })
    return out


def reset(home, platform=None, action=None):
    """Clear buckets (testing / manual recovery)."""
    data = _load(home)
    if platform is None:
        data = {}
    else:
        key = f"{platform}:{action}" if action else None
        for k in [k for k in data if k == key or
                  (key is None and k.split(":")[0] == platform)]:
            del data[k]
    _save(home, data)
