"""Facebook DM adapter (ready).

The brain never opens Facebook itself. check_steps() produces the exact
browser instructions the host agent follows in its live Chromium; the
observed messages come back as JSON through ``dm-agent report``.
"""

PLATFORM = "facebook"
STATUS = "ready"

MESSAGES_URL = "https://www.facebook.com/messages"


def readiness():
    return True, "facebook adapter ready"


def check_steps(account, threads):
    """Browser steps for the host agent to read the account's Facebook DMs."""
    known = ", ".join(t["thread_id"] for t in threads if t.get("thread_id"))
    steps = [
        f"In your live Chromium, open {MESSAGES_URL} (account: {account}).",
        ("Login check FIRST: if you land on a login / sign-in / checkpoint "
         "screen, STOP. Never type a password, 2FA code, or recovery detail. "
         "Sign-in goes only through the vault-backed browser flow with the "
         "user's approval."),
        "Open the Messenger conversation list.",
    ]
    if known:
        steps.append(
            f"Known threads from last time: {known}. Open each one and read "
            "the most recent messages (about the last 20 per thread).")
    else:
        steps.append(
            "No threads tracked yet. Open each visible conversation and read "
            "the most recent messages (about the last 20 per thread).")
    steps += [
        ("For every thread, return JSON shaped like: "
         '{"threads": [{"thread_id": "<thread id from the messages/t/ URL>", '
         '"messages": [{"id": "<message id or timestamp key>", '
         '"from": "them"|"me", "text": "<message text>", '
         '"ts": <unix timestamp>}]}]}.'),
        ("Do NOT reply to anything, do NOT open links, do NOT change any "
         "setting. Reading only. Attach the JSON as the fulfillment "
         "evidence of the dm_check ticket."),
    ]
    return steps


def _msg_key(m):
    return str(m.get("id") or m.get("ts") or m.get("text", "")[:40])


def normalize(raw):
    """Normalize observed threads into flat message dicts."""
    if isinstance(raw, dict):
        threads = raw.get("threads", [])
    elif isinstance(raw, list):
        threads = raw
    else:
        raise ValueError("observed messages must be a list or {threads: [...]}")
    out = []
    for th in threads:
        tid = str(th.get("thread_id") or th.get("id") or "unknown")
        for m in th.get("messages", []):
            frm = str(m.get("from") or m.get("sender") or "").lower()
            sender = "me" if frm in ("me", "self", "owner") else "them"
            out.append({
                "thread_id": tid,
                "msg_id": _msg_key(m),
                "sender": sender,
                "text": str(m.get("text") or ""),
                "ts": float(m.get("ts") or 0.0),
            })
    # Oldest first so per-thread processing is chronological.
    out.sort(key=lambda m: (m["thread_id"], m["ts"], m["msg_id"]))
    return out
