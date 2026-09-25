"""Channel watcher: new uploads/posts in a channel (YouTube channel, subreddit...)."""

from ..framework import Watcher


class ChannelWatcher(Watcher):
    type = "channel"
    description = "Watches a channel (e.g. YouTube channel, subreddit) for new uploads or posts."
    schema = {
        "required": ["channel"],
        "optional": {"kinds": ["upload", "post"]},
    }

    def detect(self, items):
        cfg = self.effective_config()
        kinds = set(cfg["kinds"])
        events = []
        for it in items:
            kind = str(it.get("kind", "post"))
            if kind not in kinds:
                continue
            title = it.get("title") or it.get("text", "")
            events.append(
                self.make_event(
                    item_id=str(it.get("id")),
                    kind=f"channel:{kind}",
                    summary=f"new {kind} in {cfg['channel']}: {str(title)[:100]}",
                    data=it,
                )
            )
        return events
