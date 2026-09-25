"""People memory database (stdlib only, JSON per account)."""

import json
import os
from datetime import datetime, timezone

PEOPLE_DIR = "people"

KINDS = ("comment", "like", "dm", "follow", "mention")

# Interaction score weights: DMs and follows signal the strongest ties.
WEIGHTS = {"comment": 3, "like": 1, "dm": 5, "follow": 4, "mention": 2}


def _acct(account):
    return "".join(c if (c.isalnum() or c in "-_") else "_" for c in str(account))


def _path(home, account):
    return os.path.join(home, PEOPLE_DIR, f"{_acct(account)}.json")


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load(home, account):
    p = _path(home, account)
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _save(home, account, data):
    os.makedirs(os.path.join(home, PEOPLE_DIR), exist_ok=True)
    tmp = _path(home, account) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, _path(home, account))


def _key(handle):
    return str(handle or "unknown").lower().lstrip("@")


def upsert(home, account, handle, kind, text=None, sentiment=None,
           summary=None):
    """Record one interaction. kind in comment|like|dm|follow|mention."""
    if kind not in KINDS:
        raise ValueError(f"bad interaction kind {kind!r}")
    data = _load(home, account)
    k = _key(handle)
    rec = data.get(k)
    if rec is None:
        rec = _blank(k)
        data[k] = rec
    rec["counts"][kind] = rec["counts"].get(kind, 0) + 1
    rec["last_seen"] = utcnow()
    if text:
        rec["last_text"] = str(text)[:300]
    if isinstance(sentiment, (int, float)):
        rec["sentiments"] = (rec["sentiments"] + [round(sentiment, 3)])[-50:]
    if kind == "dm" and (summary or text):
        rec["conversations"].append(
            {"ts": utcnow(), "kind": "dm",
             "summary": (summary or str(text))[:300]})
        rec["conversations"] = rec["conversations"][-100:]
    _save(home, account, data)
    return rec


def get(home, account, handle):
    return _load(home, account).get(_key(handle))


def score(rec):
    """Interaction score: weighted count of all interactions."""
    counts = rec.get("counts", {})
    return sum(WEIGHTS.get(k, 0) * counts.get(k, 0) for k in WEIGHTS)


def sentiment_trend(rec):
    s = rec.get("sentiments") or []
    if not s:
        return None
    return round(sum(s) / len(s), 3)


def top(home, account, n=10):
    """Top people by interaction score (recurring followers surface here)."""
    data = _load(home, account)
    ranked = sorted(data.values(), key=score, reverse=True)
    return [(r["handle"], score(r), r) for r in ranked[:n]]


def _blank(handle):
    return {"handle": handle, "first_seen": utcnow(), "last_seen": utcnow(),
            "counts": {k: 0 for k in WEIGHTS}, "notes": [], "tags": [],
            "sentiments": [], "conversations": [], "last_text": ""}


def ensure(home, account, handle):
    """Return the record, creating a zero-interaction one if needed (so a
    note or tag can be attached to someone not yet seen interacting)."""
    data = _load(home, account)
    k = _key(handle)
    rec = data.get(k)
    if rec is None:
        rec = _blank(k)
        data[k] = rec
        _save(home, account, data)
    return rec


def add_note(home, account, handle, text):
    rec = ensure(home, account, handle)
    data = _load(home, account)
    rec = data[_key(handle)]
    rec["notes"].append({"ts": utcnow(), "text": text})
    _save(home, account, data)
    return rec


def add_tag(home, account, handle, tag):
    rec = ensure(home, account, handle)
    data = _load(home, account)
    rec = data[_key(handle)]
    tag = tag.strip().lower().replace(" ", "-")
    if tag and tag not in rec["tags"]:
        rec["tags"].append(tag)
    _save(home, account, data)
    return rec


def remove_tag(home, account, handle, tag):
    data = _load(home, account)
    k = _key(handle)
    rec = data.get(k)
    if rec is None:
        raise KeyError(f"unknown person {handle!r}")
    tag = tag.strip().lower().replace(" ", "-")
    if tag in rec["tags"]:
        rec["tags"].remove(tag)
    _save(home, account, data)
    return rec


def qualifies_as_top_fan(home, account, handle):
    """Score-based qualification: sustained engagement (score >= 15 with
    at least 5 comments/likes). The listener auto-tags these as top-fan."""
    rec = get(home, account, handle)
    if not rec:
        return False
    s = score(rec)
    counts = rec["counts"]
    return (s >= 15 and (counts.get("comment", 0) + counts.get("like", 0)) >= 5)


def is_top_fan(home, account, handle):
    rec = get(home, account, handle)
    return bool(rec) and "top-fan" in (rec.get("tags") or [])
