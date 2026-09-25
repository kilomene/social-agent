"""Shared hide-proposal logic (used by `moderate hide` and the `listen` router).

Creates a moderation.json record for hiding a comment on the user's OWN
comment sections. Records are proposals by default; a pre-approved
``moderation.auto_hide`` policy rule auto-approves them (still logged).
"""

import json
import os
import random
import time
from datetime import datetime, timezone

from . import classify

MODERATION_LOG = "moderation.json"


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix="m"):
    return f"{prefix}-{random.randrange(16 ** 6):06x}"


def _load(home):
    p = os.path.join(home, MODERATION_LOG)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _save(home, log):
    os.makedirs(home, exist_ok=True)
    tmp = os.path.join(home, MODERATION_LOG + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=2)
    os.replace(tmp, os.path.join(home, MODERATION_LOG))


def propose_hide(home, policy, platform, account, post, comment, text,
                 reason=""):
    """Create a hide record. Returns (record, auto_approved: bool)."""
    cls = classify.classify_comment(text or "")
    rules = (policy.get("moderation") or {}).get("auto_hide", [])
    rule = classify.check_auto_hide(text or "", rules)
    rec = {
        "id": new_id("m"), "action": "hide", "platform": platform,
        "account": account, "post": post, "comment": comment,
        "text": (text or "")[:200], "classification": cls["label"],
        "reason": reason, "dry_run": True, "created": utcnow(),
    }
    if rule:
        rec.update({"status": "approved", "auto_approved": True,
                    "auto_hide_rule": rule, "approved_at": utcnow(),
                    "approved_at_ts": time.time()})
        auto = True
    else:
        rec.update({"status": "proposed", "auto_approved": False})
        auto = False
    log = _load(home)
    log.append(rec)
    _save(home, log)
    return rec, auto


def load_log(home):
    return _load(home)


def save_log(home, log):
    _save(home, log)
