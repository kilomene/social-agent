"""Comment-section watcher: new comments on a specific post.

When config ``moderate: true``, every new comment is auto-classified by
moderation/classify.py (toxic/spam/question/praise/ok). Toxic and spam
comments become high-severity events (the crisis watcher can escalate);
comments matching a policy auto-hide rule get a hide *proposal* attached
(never executed without approval or a pre-approved rule — see `moderate`).
Classification is stored in event data so the content-idea watcher can
aggregate `question` comments and sentiment can aggregate `praise`.
"""

from ..framework import Watcher


class CommentWatcher(Watcher):
    type = "comment"
    description = "Watches the comment section of one post for new comments."
    schema = {
        "required": ["post_id"],
        "optional": {
            "propose_reply": False,
            "flag_keywords": [],
            "moderate": False,
            "auto_hide_rules": [],
        },
    }

    def detect(self, items):
        from moderation import classify as mod
        cfg = self.effective_config()
        flags = [k.lower() for k in cfg["flag_keywords"]]
        moderate = bool(cfg["moderate"])
        rules = cfg["auto_hide_rules"] or []
        events = []
        for it in items:
            text = str(it.get("text", ""))
            author = it.get("author", "unknown")
            flagged = any(k in text.lower() for k in flags)
            severity = "high" if flagged else "info"
            kind = "comment:new"
            data = dict(it)
            proposed = None
            if cfg["propose_reply"]:
                proposed = {
                    "action": "reply",
                    "target": it.get("id"),
                    "note": "Draft a reply for user approval (never auto-sent).",
                }
            if moderate:
                cls = mod.classify_comment(text)
                data["moderation"] = cls
                kind = f"comment:{cls['label']}"
                if cls["label"] in ("toxic", "spam"):
                    severity = "high"
                    rule = mod.check_auto_hide(text, rules)
                    if rule:
                        proposed = {
                            "action": "hide",
                            "target": it.get("id"),
                            "note": (f"Auto-hide rule matched ({rule['label']}: "
                                     f"{rule['reason']}). Proposes hiding; "
                                     f"requires approval unless pre-approved."),
                            "auto_hide_rule": rule,
                        }
            events.append(
                self.make_event(
                    item_id=str(it.get("id")),
                    kind=kind,
                    summary=f"new comment by @{author}: {text[:100]}",
                    data=data,
                    proposed_action=proposed,
                    severity=severity,
                )
            )
        return events
