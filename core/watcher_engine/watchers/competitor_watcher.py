"""Competitor watcher: tracks named competitor accounts.

Config: competitors: ["rival_a", "rival_b"] (required).
Items: {"id", "competitor", "followers", "follower_delta",
        "posts_last_7d", "avg_engagement", "themes": [...]}
Emits one digest event per competitor per poll with cadence, deltas and
content themes. Deltas are computed against the previous poll's snapshot
kept in watcher state (items may also carry precomputed deltas).
"""

from ..framework import Watcher, as_list


class CompetitorWatcher(Watcher):
    type = "competitor"
    description = "Tracks competitor accounts: cadence, follower/engagement deltas, themes."
    schema = {
        "required": ["competitors"],
        "optional": {},
    }

    def detect(self, items):
        wanted = {c.lower().lstrip("@") for c in as_list(self.effective_config()["competitors"])}
        prev = self._state.get("snapshots", {})
        snapshots = {}
        events = []
        for it in items:
            name = str(it.get("competitor", "")).lower().lstrip("@")
            if name not in wanted:
                continue
            followers = it.get("followers", 0)
            old = prev.get(name, {})
            f_delta = it.get("follower_delta",
                             followers - old.get("followers", followers)
                             if old else 0)
            e_delta = it.get("engagement_delta",
                             (it.get("avg_engagement") or 0) - (old.get("avg_engagement") or 0)
                             if old else 0)
            snapshots[name] = {"followers": followers,
                               "avg_engagement": it.get("avg_engagement")}
            themes = ", ".join(it.get("themes", [])[:5]) or "n/a"
            events.append(
                self.make_event(
                    item_id=str(it.get("id")),
                    kind="competitor:digest",
                    summary=(f"@{name}: {it.get('posts_last_7d', '?')} posts/7d, "
                             f"followers {followers} ({f_delta:+d}), "
                             f"avg engagement {it.get('avg_engagement', '?')} "
                             f"({e_delta:+.1f}), themes: {themes}"),
                    data={**it, "follower_delta": f_delta,
                          "engagement_delta": round(e_delta, 2)},
                    severity="info",
                )
            )
        self._state["snapshots"] = snapshots
        return events
