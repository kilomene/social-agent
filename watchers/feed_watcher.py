"""Feed watcher: scans the home/for-you feed for keyword matches."""

from .framework import Watcher


class FeedWatcher(Watcher):
    type = "feed"
    description = "Scans the feed for posts matching configured keywords."
    schema = {
        "required": [],
        "optional": {
            "keywords": [],
            "propose_engage": False,
        },
    }

    def detect(self, items):
        cfg = self.effective_config()
        keywords = [k.lower() for k in cfg["keywords"]]
        events = []
        for it in items:
            hay = f"{it.get('text', '')} {it.get('title', '')}".lower()
            matched = [k for k in keywords if k in hay]
            if keywords and not matched:
                continue
            author = it.get("author", "unknown")
            proposed = None
            if cfg["propose_engage"]:
                proposed = {
                    "action": "like",
                    "target": it.get("id"),
                    "note": "Proposed like — requires user approval.",
                }
            events.append(
                self.make_event(
                    item_id=str(it.get("id")),
                    kind="feed:match",
                    summary=f"feed match from @{author}"
                    + (f" (keywords: {', '.join(matched)})" if matched else "")
                    + f": {str(it.get('text') or it.get('title'))[:100]}",
                    data={**it, "matched_keywords": matched},
                    proposed_action=proposed,
                )
            )
        return events
