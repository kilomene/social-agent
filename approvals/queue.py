"""Unified approval queue: propose / list / approve / reject.

State: <home>/approvals/pending.json — a list of items:
  {id, type, platform, account, ref, summary, payload, reason, risk,
   status, proposed_at, decided_at, decided_by, decision_reason, retry_at}

``ref`` points at the underlying domain record, e.g.
{"store": "actions.json", "id": "a-1f2e3d"}. Approving/rejecting flips the
underlying record through a caller-supplied callback so this module never
needs to know the domain stores' shapes.
"""

import json
import os
import random
import time
from datetime import datetime, timezone

QUEUEDIR = "approvals"
PENDING = os.path.join(QUEUEDIR, "pending.json")

STATUSES = ("pending", "approved", "rejected", "done", "expired",
            "held", "rate_limited")


def _path(home):
    return os.path.join(home, PENDING)


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix="q"):
    return f"{prefix}-{random.randrange(16 ** 6):06x}"


def _load(home):
    p = _path(home)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _save(home, items):
    os.makedirs(os.path.join(home, QUEUEDIR), exist_ok=True)
    tmp = _path(home) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(items, fh, indent=2)
    os.replace(tmp, _path(home))


def per_type_policy(policy, action_type):
    """Return 'require' or 'auto' for an action type (default: require)."""
    per = (policy.get("approvals") or {}).get("per_type") or {}
    val = per.get(action_type, "require")
    return "auto" if str(val).lower() == "auto" else "require"


def propose(home, action_type, platform, account, summary, payload=None,
            reason="", risk="normal", ref=None, status="pending",
            retry_at=None):
    """Add an item to the queue. Returns the item dict."""
    if status not in STATUSES:
        raise ValueError(f"bad status {status!r}")
    items = _load(home)
    item = {
        "id": new_id(), "type": action_type, "platform": platform,
        "account": account, "ref": ref or {}, "summary": summary,
        "payload": payload or {}, "reason": reason, "risk": risk,
        "status": status, "proposed_at": utcnow(),
        "decided_at": None, "decided_by": None, "decision_reason": "",
        "retry_at": retry_at,
    }
    items.append(item)
    _save(home, items)
    return item


def list_items(home, status=None):
    items = _load(home)
    if status:
        items = [i for i in items if i["status"] == status]
    return items


def get(home, item_id):
    for i in _load(home):
        if i["id"] == item_id:
            return i
    return None


def find_by_ref(home, store, record_id):
    for i in _load(home):
        ref = i.get("ref") or {}
        if ref.get("store") == store and ref.get("id") == record_id:
            return i
    return None


def approve(home, item_id, decided_by="user", apply_fn=None):
    """Approve a pending/held/rate_limited item.

    apply_fn(item) flips the underlying domain record; it is optional.
    Returns the updated item.
    """
    items = _load(home)
    item = next((i for i in items if i["id"] == item_id), None)
    if item is None:
        raise KeyError(f"unknown approval item {item_id!r}")
    if item["status"] not in ("pending", "held", "rate_limited"):
        raise ValueError(f"item {item_id} is {item['status']}, not approvable")
    if apply_fn is not None:
        apply_fn(item)
    item["status"] = "approved"
    item["decided_at"] = utcnow()
    item["decided_by"] = decided_by
    item["approved_at_ts"] = time.time()
    _save(home, items)
    return item


def reject(home, item_id, reason="", decided_by="user", apply_fn=None):
    items = _load(home)
    item = next((i for i in items if i["id"] == item_id), None)
    if item is None:
        raise KeyError(f"unknown approval item {item_id!r}")
    if item["status"] not in ("pending", "held", "rate_limited"):
        raise ValueError(f"item {item_id} is {item['status']}, not rejectable")
    if apply_fn is not None:
        apply_fn(item, reason)
    item["status"] = "rejected"
    item["decided_at"] = utcnow()
    item["decided_by"] = decided_by
    item["decision_reason"] = reason
    _save(home, items)
    return item


def set_status(home, item_id, status, **extra):
    """Low-level status move (used by crisis hold / rate-limit flows)."""
    if status not in STATUSES:
        raise ValueError(f"bad status {status!r}")
    items = _load(home)
    item = next((i for i in items if i["id"] == item_id), None)
    if item is None:
        raise KeyError(f"unknown approval item {item_id!r}")
    item["status"] = status
    item.update(extra)
    _save(home, items)
    return item
