"""Activity watcher: tracks own-account metric changes (followers, posts)."""

from ..framework import Watcher


class ActivityWatcher(Watcher):
    type = "activity"
    description = "Tracks own account activity: follower count and post count changes."
    schema = {
        "required": [],
        "optional": {"metrics": ["followers", "posts"]},
    }

    def detect(self, items):
        if not items:
            return []
        cfg = self.effective_config()
        metrics = cfg["metrics"]
        current = items[-1]  # latest snapshot wins
        prev = (self._state.get("last_snapshot") or {})
        events = []
        for m in metrics:
            if m not in current:
                continue
            old, new = prev.get(m), current[m]
            if old is not None and old != new:
                delta = new - old if isinstance(new, (int, float)) else 0
                events.append(
                    self.make_event(
                        item_id=f"{m}-{current.get('id', 'snapshot')}",
                        kind=f"activity:{m}",
                        summary=f"{m}: {old} -> {new} ({delta:+})",
                        data={"metric": m, "old": old, "new": new, "delta": delta},
                        severity="info",
                    )
                )
        self._state["last_snapshot"] = {m: current[m] for m in metrics if m in current}
        return events
