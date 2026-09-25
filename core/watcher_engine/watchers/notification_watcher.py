"""Notification watcher: mentions, replies, likes, follows on an account."""

from ..framework import Watcher


class NotificationWatcher(Watcher):
    type = "notification"
    description = "Polls account notifications (mentions, replies, likes, follows) and proposes responses."
    schema = {
        "required": [],
        "optional": {
            "kinds": ["mention", "reply", "like", "follow"],
            "propose_reply": True,
        },
    }

    def detect(self, items):
        cfg = self.effective_config()
        kinds = set(cfg["kinds"])
        events = []
        for it in items:
            kind = str(it.get("kind", "notification"))
            if kind not in kinds:
                continue
            author = it.get("author", "unknown")
            text = it.get("text", "")
            summary = f"{kind} from @{author}" + (f": {text[:80]}" if text else "")
            proposed = None
            if cfg["propose_reply"] and kind in ("mention", "reply"):
                proposed = {
                    "action": "reply",
                    "target": it.get("id"),
                    "note": "Draft a reply for user approval (never auto-sent).",
                }
            severity = "high" if kind in ("mention", "reply") else "info"
            events.append(
                self.make_event(
                    item_id=str(it.get("id")),
                    kind=f"notification:{kind}",
                    summary=summary,
                    data=it,
                    proposed_action=proposed,
                    severity=severity,
                )
            )
        return events
