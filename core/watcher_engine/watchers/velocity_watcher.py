"""Velocity watcher: viral-velocity detector for your niche.

Flags posts gaining engagement abnormally fast — an early alert so you can
engage or create a response while the topic is hot.

Items: {"id", "author", "text", "title", "likes", "comments", "shares",
        "age_hours"}.
velocity = (likes + 3*comments + 5*shares) / max(age_hours, 0.1).
An item alerts when it matches niche_keywords and velocity >= min_velocity.
Optionally proposes a like, but only when the post scores as interesting
(selective engagement — never spam).
"""

from engagement.interest import load_profile, score_post

from ..framework import Watcher, as_list


class VelocityWatcher(Watcher):
    type = "velocity"
    description = "Early-alert detector for fast-rising posts in your niche."
    schema = {
        "required": [],
        "optional": {
            "niche_keywords": [],
            "min_velocity": 500,
            "propose_engage": False,
            "use_interest_profile": True,
        },
    }

    @staticmethod
    def velocity(it):
        likes = it.get("likes", 0) or 0
        comments = it.get("comments", 0) or 0
        shares = it.get("shares", 0) or 0
        age = it.get("age_hours", 1) or 1
        return (likes + 3 * comments + 5 * shares) / max(age, 0.1)

    def detect(self, items):
        cfg = self.effective_config()
        niche = [k.lower() for k in as_list(cfg["niche_keywords"])]
        profile = load_profile() if cfg["use_interest_profile"] else None
        events = []
        for it in items:
            hay = f"{it.get('text', '')} {it.get('title', '')}".lower()
            if niche and not any(k in hay for k in niche):
                continue
            vel = self.velocity(it)
            if vel < cfg["min_velocity"]:
                continue
            proposed = None
            if cfg["propose_engage"] and profile is not None:
                _, _, interesting = score_post(it, profile)
                if interesting:
                    proposed = {
                        "action": "like",
                        "target": it.get("id"),
                        "note": "Proposed like on fast-rising niche post — needs approval.",
                    }
            elif cfg["propose_engage"]:
                proposed = {
                    "action": "like",
                    "target": it.get("id"),
                    "note": "Proposed like on fast-rising niche post — needs approval.",
                }
            events.append(
                self.make_event(
                    item_id=str(it.get("id")),
                    kind="velocity:viral",
                    summary=(f"viral velocity {vel:,.0f}/h: @{it.get('author', '?')} — "
                             f"{str(it.get('text') or it.get('title'))[:90]}"),
                    data={**it, "velocity_per_hour": round(vel, 1)},
                    proposed_action=proposed,
                    severity="alert",
                )
            )
        return events
