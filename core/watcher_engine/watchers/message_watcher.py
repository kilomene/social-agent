"""Message watcher: new DMs / inbox messages."""

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
