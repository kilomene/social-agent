"""Trend watcher: watches trending hashtags/topics/sounds per platform.

Items: {"id", "topic" (or "hashtag"/"sound"), "heat" (0-100),
        "delta" (heat change vs previous period), "examples": [...]}
Emits one event per emerging trend (heat >= min_heat) with a proposed
content angle. When use_interest_profile is true, off-mission trends are
filtered out instead of proposed.
"""

from engagement.interest import load_profile, score_post

from ..framework import Watcher


class TrendWatcher(Watcher):
    type = "trend"
    description = "Tracks trending topics/hashtags/sounds and proposes content angles."
    schema = {
        "required": [],
        "optional": {
            "min_heat": 60,
            "min_delta": 0,
            "use_interest_profile": False,
            "propose_content": True,
        },
    }

    def detect(self, items):
        cfg = self.effective_config()
        profile = load_profile() if cfg["use_interest_profile"] else None
        events = []
        for it in items:
            topic = it.get("topic") or it.get("hashtag") or it.get("sound") or "?"
            heat = it.get("heat", 0)
            delta = it.get("delta", 0)
            if heat < cfg["min_heat"] or delta < cfg["min_delta"]:
                continue
            item = {"text": f"{topic} {' '.join(it.get('examples', []))}",
                    "hashtags": [topic.lstrip("#")]}
            in_scope, reasons = True, []
            if profile is not None:
                score, reasons, in_scope = score_post(item, profile)
            if not in_scope:
                continue  # off-mission trend: filtered, not proposed
            proposed = None
            if cfg["propose_content"]:
                proposed = {
                    "action": "post",
                    "target": f"trend:{topic}",
                    "note": (f"Content angle: '{topic}' is trending "
                             f"(heat {heat}, +{delta}). Draft a post riding it. "
                             f"Interest: {'; '.join(reasons[:2])}"),
                }
            events.append(
                self.make_event(
                    item_id=str(it.get("id")),
                    kind="trend:emerging",
                    summary=f"trending: {topic} (heat {heat}, +{delta})",
                    data={**it, "topic": topic},
                    proposed_action=proposed,
                    severity="info",
                )
            )
        return events
