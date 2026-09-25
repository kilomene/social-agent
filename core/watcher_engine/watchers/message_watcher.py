"""Message watcher: new DMs / inbox messages.

RETIRED for x / tiktok / instagram / facebook (2026-09-25): DMs are owned
EXCLUSIVELY by dm_agents/ now, so the watcher and the DM agent can never
double-handle the same conversation. The class is retained because
youtube / reddit / linkedin still register it, listen.py's people-memory
pass reads message events (it only logs senders, never drafts replies),
and the test suite + exams exercise it directly.
"""

from ..framework import Watcher


class MessageWatcher(Watcher):
    type = "message"
    description = "Watches the inbox/DMs for new messages; proposes drafted replies."
    schema = {
        "required": [],
        "optional": {"propose_reply": True},
    }

    def detect(self, items):
        cfg = self.effective_config()
        events = []
        for it in items:
            sender = it.get("sender") or it.get("author", "unknown")
            text = str(it.get("text", ""))
            proposed = None
            if cfg["propose_reply"]:
                proposed = {
                    "action": "dm",
                    "target": sender,
                    "in_reply_to": it.get("id"),
                    "note": "Draft a reply for user approval (never auto-sent).",
                }
            events.append(
                self.make_event(
                    item_id=str(it.get("id")),
                    kind="message:new",
                    summary=f"new message from @{sender}: {text[:100]}",
                    data=it,
                    proposed_action=proposed,
                    severity="high",
                )
            )
        return events
