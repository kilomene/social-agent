"""Instagram DM adapter (ready).

The brain never opens Instagram itself. check_steps() produces the exact
browser instructions the host agent follows in its live Chromium; the
observed messages come back as JSON through ``dm-agent report``.

Web DM flow verified live 2026-09-30: inbox at
https://www.instagram.com/direct/inbox/ renders a left thread list
(threads identified by handle/display name, e.g. "<handle> ... <display
name>") and the open thread in the adjacent right panel ("Message
Thread"). Requests tab at https://www.instagram.com/direct/requests/.
"""

PLATFORM = "instagram"
STATUS = "ready"

MESSAGES_URL = "https://www.instagram.com/direct/inbox/"
REQUESTS_URL = "https://www.instagram.com/direct/requests/"


def readiness():
    return True, "instagram adapter ready (web DM flow verified 2026-09-30)"


def check_steps(account, threads):
    """Browser steps for the host agent to read the account's Instagram DMs."""
    known = ", ".join(t["thread_id"] for t in threads if t.get("thread_id"))
    steps = [
        f"In your live Chromium, open {MESSAGES_URL} (account: {account}).",
        ("Login check FIRST: if you land on a login / sign-in / checkpoint "
         "screen, STOP. Never type a password, 2FA code, or recovery detail. "
         "Sign-in goes only through the vault-backed browser flow with the "
         "user's approval. Also STOP if the account switcher at the top of "
         "the Messages column shows any handle other than the one above."),
        ("Open the DM inbox and read the conversation list in the left "
         '"Messages" column. Each thread appears as a clickable link named '
         'like "<handle> ... <display name>" with an unread indicator and '
         "the time of last activity — identify threads by handle/display "
         "name, not numeric ids."),
    ]
    if known:
        steps.append(
            f"Known threads from last time: {known}. Open each one in the "
            "right-hand panel and read the most recent messages (about the "
            "last 20 per thread).")
    else:
        steps.append(
            "No threads tracked yet. Open each visible conversation in the "
            "right-hand panel and read the most recent messages (about the "
            "last 20 per thread).")
    steps += [
        (f"Also check the Requests tab ({REQUESTS_URL}) for new message "
         "requests and read any visible ones the same way."),
        ("For every thread, return JSON shaped like: "
         '{"threads": [{"thread_id": "<handle or display name>", "messages": '
         '[{"id": "<message id or timestamp key>", "from": "them"|"me", '
         '"text": "<message text>", "ts": <unix timestamp>}]}]}.'),
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
    # Oldest first so per-thread processing is chronological. Ts ties
    # break on the stable cross-cycle message fingerprint, NOT the
    # browser-invented msg_id (re-invented every read cycle; using it
    # here flipped ordering across cycles and re-flagged already-seen
    # messages as new — 2026-09-25 TikTok duplicate-draft bug).
    from dm_agents.state import message_fingerprint
    out.sort(key=lambda m: (m["thread_id"], m["ts"],
                            message_fingerprint(m["thread_id"], m)))
    return out
