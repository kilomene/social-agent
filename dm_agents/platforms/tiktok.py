"""TikTok DM adapter (ready).

Verified live 2026-09-25: TikTok DM conversation content IS readable on
the web client (https://www.tiktok.com/messages). An earlier note claimed
bodies were app-only; a live read the same day proved that wrong — full
message text renders in the browser. Only some exotic message types show
a "[This message type isn't supported...]" placeholder (likely voice
notes or unsupported media); those are reported as unsupported, never
guessed at.

The brain never opens TikTok itself. check_steps() produces the exact
browser instructions the host agent follows in its live Chromium; the
observed messages come back as JSON through ``dm-agent report``.
"""

PLATFORM = "tiktok"
STATUS = "ready"

MESSAGES_URL = "https://www.tiktok.com/messages"


def readiness():
    return True, "tiktok adapter ready (message bodies readable on web, verified 2026-09-25)"


def check_steps(account, threads):
    """Browser steps for the host agent to read the account's TikTok DMs."""
    known = ", ".join(t["thread_id"] for t in threads if t.get("thread_id"))
    steps = [
        f"In your live Chromium, open {MESSAGES_URL} (account: {account}).",
        ("Login check FIRST: if you land on a login / sign-in / checkpoint "
         "screen, STOP. Never type a password, 2FA code, or recovery detail. "
         "Sign-in goes only through the vault-backed browser flow with the "
         "user's approval."),
        "Open the DM inbox and read the conversation list (note unread badges).",
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
        ("Some messages may show as \"[This message type isn't supported. "
         "Download TikTok app to view this message.]\" — report those "
         "verbatim as unsupported; never guess what they contain."),
        ("For every thread, return JSON shaped like: "
         '{"threads": [{"thread_id": "<id or handle>", "messages": '
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
    # Oldest first so per-thread processing is chronological.
    out.sort(key=lambda m: (m["thread_id"], m["ts"], m["msg_id"]))
    return out
