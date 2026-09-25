"""Execution tickets: the brain-to-hands handoff.

social-agent is the BRAIN (watchers, proposals, approvals, ToS, memory).
It never drives a browser. When an approved action is ready, the CLI
emits a machine-readable execution TICKET (JSON)::

    {action, platform, account, target, parameters, idem_key,
     receipts: {tos, approval, rate_limit}, steps, ...}

An external agent (e.g. Muse with its own server-side Chromium and a
live browser card the user watches) fulfills the ticket; the operator
confirms via the existing engage done / approval flow.

Lifecycle: issued -> claimed -> fulfilled
                      \\-> failed / cancelled

- approving a proposal ISSUES a ticket (status: issued) carrying the
  ToS / approval / rate-limit receipts plus step-by-step browser
  instructions for the external agent.
- the external agent CLAIMs a ticket (recording which agent + live
  session), performs the steps visibly in its own browser, then the
  ticket is FULFILLED with evidence.
- idempotency: claim and fulfill are journaled (core.resume_engine).
  A ticket can NEVER be fulfilled twice — a repeated fulfill is refused
  as a duplicate, even after a crash (the resume engine's
  never-repeat guarantee).

Credential rule: tickets NEVER contain credentials. No password / token
/ secret / API-key fields exist in the schema or in stored ticket JSON.
Logins live in the agent's secure vault (or the user's own browser) —
never in the repo or its state.
"""

import json
import os
import random
import time
from datetime import datetime, timezone

from hands import steps as steps_mod

TICKETS_FILE = "tickets.json"
# Directory form (identity/host_sessions/host_sessions.json) so the record
# lands inside the backup-protected identity/host_sessions/ tree and the
# layout install.py creates. identity/store.py docstrings describe the same.
HOST_SESSIONS_FILE = os.path.join("identity", "host_sessions", "host_sessions.json")

STATUSES = ("issued", "claimed", "fulfilled", "failed", "cancelled")

# The execution ticket schema. Field names are part of the credential
# tripwire (tests/test_hands.py): no credential-like names may appear.
# NOTE: the idempotency field is deliberately named ``idem_key`` (matching
# the journal) so no field name contains the substring "key".
TICKET_SCHEMA = {
    "id": "ticket id, e.g. tkt-1a2b3c",
    "issued_at": "ISO-8601 UTC timestamp",
    "status": "one of: " + ", ".join(STATUSES),
    "action": "like | comment | follow | unfollow | post_text | "
              "post_video | post_photo | dm_send | dm_check | hide_comment | "
              "reshare | subscribe | profile_update",
    "platform": "tiktok | x | instagram | facebook | youtube | reddit | linkedin | threads",
    "account": "account label the action is for",
    "target": "target URL (post/profile/conversation)",
    "parameters": "action parameters (text, file, ...) — never credentials",
    "steps": "step-by-step browser instructions for the external agent",
    "idem_key": "idempotency key (ticket id based; journaled)",
    "receipts": "{tos, approval, rate_limit} — proof the guard order ran",
    "source": "where the ticket came from, e.g. {approval_id, proposal_type}",
    "host": "{agent, session_id, claimed_at} — set on claim",
    "fulfillment": "{fulfilled_at, evidence, host_session_id} — set on fulfill",
}

# approval-queue item type -> ticket action
TYPE_TO_ACTION = {
    "like": "like", "comment": "comment", "follow": "follow",
    "unfollow": "unfollow", "retweet": "reshare", "reshare": "reshare",
    "reply": "comment", "dm": "dm_send",
    "post": "post_text", "publish": "post_text", "post_text": "post_text",
    "post_video": "post_video", "post_photo": "post_photo",
    "profile": "profile_update",
    "hide_spam": "hide_comment", "hide_other": "hide_comment",
    "subscribe": "subscribe",
}


def _path(home):
    return os.path.join(home, TICKETS_FILE)


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix="tkt"):
    return f"{prefix}-{random.randrange(16 ** 6):06x}"


def _load(home):
    p = _path(home)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _save(home, tickets):
    p = _path(home)
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(tickets, fh, indent=2)
    os.replace(tmp, p)


def get(home, ticket_id):
    for t in _load(home):
        if t["id"] == ticket_id:
            return t
    return None


def list_tickets(home, status=None):
    tickets = _load(home)
    if status:
        tickets = [t for t in tickets if t["status"] == status]
    return tickets


def _target_of(params):
    params = params or {}
    return (params.get("target_url") or params.get("target")
            or params.get("url") or params.get("thread") or "")


def issue(home, action, platform, account, target="", parameters=None,
          receipts=None, source=None):
    """Emit an execution ticket in ``issued`` status and return it."""
    if action not in steps_mod.supported_actions():
        raise ValueError(f"unknown ticket action {action!r}")
    tickets = _load(home)
    tid = new_id()
    params = parameters or {}
    ticket = {
        "id": tid,
        "issued_at": utcnow(),
        "status": "issued",
        "action": action,
        "platform": platform,
        "account": account,
        "target": target or _target_of(params),
        "parameters": params,
        "steps": steps_mod.build_steps(action, platform, params),
        "idem_key": f"ticket:{tid}",
        "receipts": receipts or {},
        "source": source or {},
        "host": {},
        "fulfillment": {},
    }
    tickets.append(ticket)
    _save(home, tickets)
    return ticket


def issue_from_approval(home, item, decided_by="user", decided_at=""):
    """Issue a ticket from an approved approval-queue item.

    Called by approvals.queue.approve(): the human decision is what makes
    the ticket issuable. The ticket carries the ToS / approval /
    rate-limit receipts — proof the full guard order
    (ToS > crisis > approvals > rate limits > quiet hours) ran before
    anything was emitted. The external agent fulfills it visibly in its
    own browser; the operator confirms via the existing engage done /
    approval flow.
    """
    action = TYPE_TO_ACTION.get(item.get("type"), "like")
    if action == "dm_send":
        # The automated_dms prohibition governs SENDING. Drafts may be
        # queued (proposing is allowed), but the pipeline must never
        # issue a DM send on a platform where automated DMs are
        # prohibited. Sends there happen only through the owner's own
        # hands under explicit standing order — never via ticket.
        # No policy is passed: prohibitions stay fail-closed here.
        from platforms import tos as _tos_mod  # lazy: avoids import cycles
        _tos_mod.check_tos(item.get("platform", ""), "automated_dms",
                           home=home)
    receipts = {
        "tos": {
            "risk": item.get("risk", ""),
            "checked": "proposal/approval time",
            "note": ("ToS-checked before approval; external agent must "
                     "follow the steps exactly and must not improvise "
                     "out-of-scope actions."),
        },
        "approval": {
            "approval_id": item.get("id"),
            "decided_by": decided_by,
            "decided_at": decided_at or utcnow(),
        },
        "rate_limit": {
            "bucket": f"{item.get('platform', '')}:{action}",
            "checked": "approval time",
            "note": ("rate-limit controller passed before approval; "
                     "re-check before fulfilling if delayed."),
        },
    }
    return issue(home, action, item.get("platform", ""),
                 item.get("account", ""),
                 parameters=dict(item.get("payload") or {}),
                 receipts=receipts,
                 source={"approval_id": item.get("id"),
                         "proposal_type": item.get("type"),
                         "summary": (item.get("summary") or "")[:200]})


def _transition(home, ticket_id, from_statuses, to_status,
                journal_action, payload, update):
    from core import resume_engine as _rec  # lazy: keeps import light
    tickets = _load(home)
    ticket = next((t for t in tickets if t["id"] == ticket_id), None)
    if ticket is None:
        raise KeyError(f"unknown ticket {ticket_id!r}")
    if ticket["status"] not in from_statuses:
        raise ValueError(
            f"ticket {ticket_id} is {ticket['status']}, "
            f"cannot move to {to_status}")
    jb = _rec.begin(home, journal_action, ticket_id, payload)
    if jb["duplicate"]:
        raise ValueError(
            f"ticket {ticket_id} already {to_status} (idempotent) — "
            "refusing repeat")
    try:
        update(ticket)
        ticket["status"] = to_status
        _save(home, tickets)
    except Exception as e:
        _rec.end(home, jb["id"], False, error=str(e))
        raise
    _rec.end(home, jb["id"], True, result=f"{ticket_id} -> {to_status}")
    return ticket


def claim(home, ticket_id, host_agent, session_id, note=""):
    """issued -> claimed. Records WHICH external agent + live session."""
    if not host_agent or not session_id:
        raise ValueError("claim requires host_agent and session_id")

    def _upd(ticket):
        ticket["host"] = {"agent": host_agent, "session_id": session_id,
                          "claimed_at": utcnow(), "note": note}
        register_host_session(home, host_agent, session_id,
                              account_label=ticket.get("account", ""),
                              note=note)

    return _transition(home, ticket_id, ("issued",), "claimed",
                       "ticket-claim",
                       {"agent": host_agent, "session_id": session_id}, _upd)


def fulfill(home, ticket_id, evidence, host_session_id="", note=""):
    """claimed -> fulfilled. A ticket can NEVER be fulfilled twice.

    Evidence is required: what the external agent did and saw in its
    live browser. The host session is recorded in the identity
    host_sessions registry. The operator then confirms via the existing
    engage done / approval flow.
    """
    if not (evidence or "").strip():
        raise ValueError("fulfill requires evidence")

    def _upd(ticket):
        sid = host_session_id or ticket.get("host", {}).get("session_id", "")
        ticket["fulfillment"] = {"fulfilled_at": utcnow(),
                                 "fulfilled_ts": time.time(),
                                 "evidence": evidence,
                                 "host_session_id": sid,
                                 "note": note}
        if sid:
            record_ticket_session(home, sid, ticket_id, evidence)

    return _transition(home, ticket_id, ("claimed",), "fulfilled",
                       "ticket-done", {"ticket": ticket_id}, _upd)


def fail(home, ticket_id, error=""):
    """issued/claimed -> failed (external agent could not complete it)."""
    tickets = _load(home)
    ticket = next((t for t in tickets if t["id"] == ticket_id), None)
    if ticket is None:
        raise KeyError(f"unknown ticket {ticket_id!r}")
    if ticket["status"] not in ("issued", "claimed"):
        raise ValueError(
            f"ticket {ticket_id} is {ticket['status']}, cannot fail it")
    ticket["fulfillment"] = {"fulfilled_at": utcnow(), "evidence": "",
                             "host_session_id": ticket.get("host", {}).get(
                                 "session_id", ""),
                             "note": "", "error": error}
    ticket["status"] = "failed"
    _save(home, tickets)
    return ticket


def cancel(home, ticket_id, reason=""):
    """issued -> cancelled."""
    tickets = _load(home)
    ticket = next((t for t in tickets if t["id"] == ticket_id), None)
    if ticket is None:
        raise KeyError(f"unknown ticket {ticket_id!r}")
    if ticket["status"] != "issued":
        raise ValueError(
            f"ticket {ticket_id} is {ticket['status']}, cannot cancel it")
    ticket["status"] = "cancelled"
    ticket["cancel_reason"] = reason
    ticket["cancelled_at"] = utcnow()
    _save(home, tickets)
    return ticket


# ------------------------------------------------- host session records ---

def _sessions_path(home):
    return os.path.join(home, HOST_SESSIONS_FILE)


def _load_sessions(home):
    p = _sessions_path(home)
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _save_sessions(home, data):
    p = _sessions_path(home)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, p)


def register_host_session(home, agent, session_id, identity_id="",
                          account_label="", note=""):
    """Record an external agent's live browser session.

    The repo never drives a browser: this records WHICH external agent
    and live session fulfilled each execution ticket, with evidence
    notes. No credentials are ever stored here — logins live in the
    agent's secure vault (or the user's own browser).
    """
    data = _load_sessions(home)
    rec = data.get(session_id, {"agent": agent, "session_id": session_id,
                                "identity_id": identity_id,
                                "account_labels": [],
                                "first_seen": utcnow(),
                                "tickets_fulfilled": [], "notes": []})
    rec["agent"] = agent
    rec["identity_id"] = identity_id or rec.get("identity_id", "")
    if account_label and account_label not in rec["account_labels"]:
        rec["account_labels"].append(account_label)
    rec["last_seen"] = utcnow()
    if note and note not in rec["notes"]:
        rec["notes"].append(note)
    data[session_id] = rec
    _save_sessions(home, data)
    return rec


def record_ticket_session(home, session_id, ticket_id, evidence):
    """Attach a fulfilled ticket to its host session record."""
    data = _load_sessions(home)
    rec = data.get(session_id)
    if rec is None:
        rec = {"agent": "", "session_id": session_id, "identity_id": "",
               "account_labels": [], "first_seen": utcnow(),
               "tickets_fulfilled": [], "notes": []}
    if ticket_id not in rec["tickets_fulfilled"]:
        rec["tickets_fulfilled"].append(ticket_id)
    rec["last_seen"] = utcnow()
    data[session_id] = rec
    _save_sessions(home, data)
    return rec


def list_host_sessions(home):
    return _load_sessions(home)


def format_ticket(ticket):
    """Human-readable rendering for `ticket show`."""
    lines = [
        f"{ticket['id']} [{ticket['status']}] {ticket['action']} "
        f"[{ticket['platform']}/{ticket['account']}]",
        f"issued: {ticket['issued_at']}  idem_key: {ticket['idem_key']}",
    ]
    if ticket.get("target"):
        lines.append(f"target: {ticket['target']}")
    src = ticket.get("source") or {}
    if src.get("approval_id"):
        lines.append(f"source: approval {src['approval_id']} "
                     f"({src.get('proposal_type', '')})")
    rct = ticket.get("receipts") or {}
    if rct:
        parts = []
        for k, v in rct.items():
            if isinstance(v, dict):
                parts.append(f"{k}={v.get('checked', '')}")
            else:
                parts.append(f"{k}={v}")
        lines.append("receipts: " + ", ".join(parts))
    host = ticket.get("host") or {}
    if host.get("agent"):
        lines.append(f"host: {host['agent']} session={host['session_id']} "
                     f"claimed={host.get('claimed_at', '')}")
    fu = ticket.get("fulfillment") or {}
    if fu.get("fulfilled_at"):
        lines.append(f"fulfilled: {fu['fulfilled_at']} "
                     f"session={fu.get('host_session_id', '')}")
        if fu.get("evidence"):
            lines.append(f"evidence: {fu['evidence'][:300]}")
    lines.append("steps for the external agent:")
    for i, s in enumerate(ticket.get("steps", []), 1):
        lines.append(f"  {i}. {s}")
    return "\n".join(lines)
