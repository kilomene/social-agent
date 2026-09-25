"""Comment-section watcher: new comments on a specific post."""

from .framework import Watcher


class CommentWatcher(Watcher):
    type = "comment"
    description = "Watches the comment section of one post for new comments."
    schema = {
        "required": ["post_id"],
        "optional": {
            "propose_reply": False,
            "flag_keywords": [],
        },
    }

    def detect(self, items):
        cfg = self.effective_config()
        flags = [k.lower() for k in cfg["flag_keywords"]]
        events = []
        for it in items:
            text = str(it.get("text", ""))
            author = it.get("author", "unknown")
            flagged = any(k in text.lower() for k in flags)
            proposed = None
            if cfg["propose_reply"]:
                proposed = {
                    "action": "reply",
                    "target": it.get("id"),
                    "note": "Draft a reply for user approval (never auto-sent).",
                }
            events.append(
                self.make_event(
                    item_id=str(it.get("id")),
                    kind="comment:new",
                    summary=f"new comment by @{author}: {text[:100]}",
                    data=it,
                    proposed_action=proposed,
                    severity="high" if flagged else "info",
                )
            )
        return events
