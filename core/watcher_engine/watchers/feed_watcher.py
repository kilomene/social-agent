"""Feed watcher: scans the home/for-you feed for keyword matches.

With use_interest_profile=true, only posts scoring as "interesting" against
the policy interest profile emit events / like proposals (selective
engagement — never spam)."""

from engagement.interest import load_profile, score_post

from ..framework import Watcher


class FeedWatcher(Watcher):
    type = "feed"
    description = "Scans the feed for posts matching configured keywords."
    schema = {
        "required": [],
        "optional": {
            "keywords": [],
            "propose_engage": False,
            "use_interest_profile": False,
        },
    }

    def detect(self, items):
        cfg = self.effective_config()
        keywords = [k.lower() for k in cfg["keywords"]]
        profile = load_profile() if cfg["use_interest_profile"] else None
        events = []
        for it in items:
            hay = f"{it.get('text', '')} {it.get('title', '')}".lower()
            matched = [k for k in keywords if k in hay]
            if keywords and not matched:
                continue
            score, reasons, interesting = (0, [], True)
            if profile is not None:
                score, reasons, interesting = score_post(it, profile)
                if not interesting:
                    continue  # boring post: no event, no like proposal
            author = it.get("author", "unknown")
            proposed = None
            if cfg["propose_engage"]:
                proposed = {
                    "action": "like",
                    "target": it.get("id"),
                    "note": ("Proposed like — requires user approval. "
                             f"Interest score {score}."),
                }
            events.append(
                self.make_event(
                    item_id=str(it.get("id")),
                    kind="feed:match",
                    summary=f"feed match from @{author}"
                    + (f" (keywords: {', '.join(matched)})" if matched else "")
                    + (f" [interest {score}]" if profile is not None else "")
                    + f": {str(it.get('text') or it.get('title'))[:100]}",
                    data={**it, "matched_keywords": matched,
                          "interest_score": score, "interest_reasons": reasons},
                    proposed_action=proposed,
                )
            )
        return events
