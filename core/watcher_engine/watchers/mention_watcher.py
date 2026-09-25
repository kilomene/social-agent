"""Mention watcher: unified cross-platform @mention/tag watcher.

Distinct from the per-platform notification watcher: one mention watcher
tracks mentions of your handles wherever they appear. Config `accounts`
lists the handles to watch for (defaults to the watcher's own account).

Items: {"id", "mentioned_account", "author", "text", "url"}.
Emits an event per new mention; optionally proposes a reply.
"""

from ..framework import Watcher, as_list


class MentionWatcher(Watcher):
    type = "mention"
    description = "Unified @mention/tag watcher for your accounts."
    schema = {
        "required": [],
        "optional": {
            "accounts": [],
            "propose_reply": False,
        },
    }

    def detect(self, items):
        cfg = self.effective_config()
        handles = {a.lower().lstrip("@") for a in as_list(cfg["accounts"])}
        if not handles:
            handles = {self.account.lower().lstrip("@")}
        events = []
        for it in items:
            m = str(it.get("mentioned_account", "")).lower().lstrip("@")
            if m not in handles:
                continue
            proposed = None
            if cfg["propose_reply"]:
                proposed = {
                    "action": "comment",
                    "target": it.get("id"),
                    "note": "Proposed reply to mention — requires user approval.",
                }
            events.append(
                self.make_event(
                    item_id=str(it.get("id")),
                    kind="mention:tagged",
                    summary=(f"@{it.get('author', '?')} mentioned @{m}: "
                             f"{str(it.get('text'))[:100]}"),
                    data=it,
                    proposed_action=proposed,
                )
            )
        return events
