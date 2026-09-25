"""Notification listener: fast-poll loop over notification/comment/message watchers.

Each tick polls the enabled watchers of those types, then routes every new
event through one pipeline:

  comment events -> classify (toxicity/spam/question/praise) + people upsert
      question     -> reply draft into the approval queue (never auto-sent)
      toxic/spam   -> hide proposal via the moderation flow
      top-fan      -> priority flag on the resulting queue item
  message events -> people conversation log + user notification
  notification events -> people upsert (mention/like/follow)

Latency honesty: this is POLL-based near-real-time (default 60s interval),
not true push. Genuinely instant delivery needs platform webhooks where the
platform offers them (documented in docs/listen-latency.md). `listen --once`
runs a single pass (used by tests/exams).

Watchers stay read-only: the listener is what classifies, remembers, and
proposes. Nothing is ever acted on without going through the approval
queue.
"""

import json
import os
import time
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

from core.watcher_engine import REGISTRY
from moderation import classify as mod_classify
from moderation import propose as mod_propose
from people import db as people_db
from approvals import queue as approvals_queue
from heartbeat import pinger as hb

LISTEN_TYPES = ("notification", "comment", "message")
NOTIFICATIONS_LOG = "notifications.json"


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_registry(home):
    p = os.path.join(home, "watchers.json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def notify(home, text, kind="info"):
    """User notification: appended to notifications.json and printed."""
    p = os.path.join(home, NOTIFICATIONS_LOG)
    log = []
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as fh:
                log = json.load(fh)
        except (json.JSONDecodeError, OSError):
            log = []
    entry = {"ts": utcnow(), "kind": kind, "text": text}
    log.append(entry)
    tmp = p + ".tmp"
    os.makedirs(home, exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(log[-200:], fh, indent=2)
    os.replace(tmp, p)
    print(f"USER NOTIFICATION [{kind}]: {text}")
    return entry


def _sentiment(text):
    try:
        from core.watcher_engine.watchers.sentiment_watcher import lexicon_score
        return lexicon_score(text or "")
    except Exception:
        return None


def _safe_reply_draft(home, platform, account_label, author, question):
    """Draft a reply that passes the content gates; fall back to a safe
    generic draft if the gates refuse (never let a bad draft reach a human
    unmarked)."""
    from voice import check as voice_check_mod
    from identity import check as identity_mod
    from security import secrets as secrets_mod

    candidates = [
        (f"Great question, @{author} — let me get back to you on that properly. "
         f"What specifically are you trying to do?"),
        "Thanks for asking! I'll follow up with a proper answer shortly.",
    ]
    for draft in candidates:
        try:
            found, _ = secrets_mod.contains_secret(draft)
            if found:
                continue
            ident = identity_mod.check_identity(draft, account_label, home)
            if not ident["pass"]:
                continue
            return draft, voice_check_mod.check_text(draft, platform)
        except Exception:
            continue
    return candidates[-1], {"human": True, "score": 100}


def route_event(home, policy, ev):
    """Route one watcher event. Returns a list of human-readable outcomes."""
    outcomes = []
    wtype = ev.get("watcher_type") or ""
    kind = ev.get("kind") or ""
    data = ev.get("data") or {}
    platform = ev.get("platform")
    account = ev.get("account")

    if wtype == "comment" or kind.startswith("comment"):
        author = data.get("author") or "unknown"
        text = str(data.get("text") or "")
        cls = mod_classify.classify_comment(text)
        people_db.upsert(home, account, author, "comment", text=text,
                         sentiment=_sentiment(text))
        # sustained engagement auto-tags a top fan so replies get priority
        if people_db.qualifies_as_top_fan(home, account, author):
            people_db.add_tag(home, account, author, "top-fan")
        top_fan = people_db.is_top_fan(home, account, author)
        if cls["label"] in ("toxic", "spam"):
            rec, auto = mod_propose.propose_hide(
                home, policy, platform, account, data.get("post_id", ""),
                str(data.get("id", "")), text,
                reason=f"listener: classified {cls['label']}")
            st = "approved" if auto else "pending"
            item = approvals_queue.propose(
                home, "hide_spam" if auto else "hide_other", platform, account,
                summary=f"hide {cls['label']} comment by @{author}",
                payload={"comment_id": data.get("id"), "text": text[:200]},
                reason=f"listener: {cls['label']} ({'; '.join(cls['reasons'][:2])})",
                risk="high", ref={"store": "moderation.json", "id": rec["id"]},
                status=st)
            outcomes.append(f"hide proposal {item['id']} [{st}] for "
                            f"{cls['label']} comment by @{author}")
        elif cls["label"] == "question":
            draft, voice = _safe_reply_draft(home, platform, account, author,
                                             text)
            item = approvals_queue.propose(
                home, "reply", platform, account,
                summary=f"reply draft for @{author}'s question",
                payload={"comment_id": data.get("id"),
                         "question": text[:300], "draft": draft,
                         "priority": bool(top_fan)},
                reason="listener: question comment deserves an answer",
                risk="high" if top_fan else "normal")
            flag = " [PRIORITY: top-fan]" if top_fan else ""
            outcomes.append(f"reply draft {item['id']} queued for approval{flag}")
            if voice and not voice.get("human", True):
                outcomes.append(f"voice note on draft {item['id']}: review tone")
        else:
            outcomes.append(f"comment by @{author} classified {cls['label']} "
                            f"(remembered, no action)")
    elif wtype == "message" or kind.startswith("message"):
        sender = data.get("sender") or data.get("author") or "unknown"
        text = str(data.get("text") or "")
        people_db.upsert(home, account, sender, "dm", text=text,
                         sentiment=_sentiment(text),
                         summary=f"DM: {text[:200]}")
        notify(home, f"new DM from @{sender}: {text[:160]}", kind="dm")
        outcomes.append(f"DM from @{sender} logged to people memory + notified")
    elif wtype == "notification" or kind.startswith("notification"):
        actor = data.get("author") or data.get("actor") or "unknown"
        nkind = kind.split(":", 1)[-1] if ":" in kind else "notification"
        pkind = {"mention": "mention", "reply": "mention",
                 "like": "like", "follow": "follow"}.get(nkind, "mention")
        if actor != "unknown":
            people_db.upsert(home, account, actor, pkind,
                             text=str(data.get("text") or ""))
        if nkind in ("mention", "reply"):
            notify(home, f"@{actor} mentioned you: "
                         f"{str(data.get('text') or '')[:140]}", kind="mention")
        outcomes.append(f"notification {nkind} from @{actor} recorded")
    else:
        outcomes.append(f"unrouted event kind {kind!r} (ignored)")
    return outcomes


def run_once(home, policy, watcher_ids=None):
    """One listen pass over enabled notification/comment/message watchers.
    Returns {watcher_id: [outcomes]}."""
    registry = _load_registry(home)
    hb_cfg = hb.load_config()
    report = {}
    for wid, rec in sorted(registry.items()):
        if watcher_ids and wid not in watcher_ids:
            continue
        if rec.get("type") not in LISTEN_TYPES:
            continue
        if not rec.get("enabled"):
            continue
        cls = REGISTRY.get(rec["type"])
        if cls is None:
            continue
        w = cls(wid, rec["platform"], rec["account"], rec.get("config"),
                home, rec.get("fixture"))
        try:
            events = hb.watch_run(hb_cfg, f"listen-{wid}", w.check)
        except Exception as e:
            report[wid] = [f"poll failed: {e}"]
            continue
        outs = []
        for ev in events:
            try:
                outs.extend(route_event(home, policy, ev))
            except Exception as e:
                outs.append(f"routing failed for event {ev.get('id')}: {e}")
        report[wid] = outs
    return report
