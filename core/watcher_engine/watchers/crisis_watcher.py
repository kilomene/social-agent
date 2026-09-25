"""Crisis watcher: negative-spike early warning.

Watches for a sudden surge of negative sentiment or negative keywords about
your accounts and fires one URGENT event per spike window (cooldown prevents
repeat alerts for the same spike).

Items: {"id", "account", "text", "timestamp", "sentiment" (optional, -1..1)}.
Negative = sentiment < -0.4, or a negative_keywords hit, or the lexicon
score (shared with the sentiment watcher) < -0.4.
"""

from datetime import datetime, timezone

from ..framework import Watcher, as_list
from .sentiment_watcher import lexicon_score


def _ts(item):
    try:
        return datetime.fromisoformat(str(item.get("timestamp")).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


class CrisisWatcher(Watcher):
    type = "crisis"
    description = "Early warning for negative-sentiment spikes about your accounts."
    schema = {
        "required": [],
        "optional": {
            "accounts": [],
            "negative_keywords": ["scam", "fake", "hate", "terrible", "awful",
                                  "boycott", "exposed", "cancel"],
            "spike_threshold": 5,
            "window_hours": 6,
            "alert_cooldown_hours": 12,
            "auto_pause": False,
        },
    }

    def is_negative(self, item, keywords):
        s = item.get("sentiment")
        if isinstance(s, (int, float)) and s < -0.4:
            return True
        hay = str(item.get("text", "")).lower()
        if any(k.lower() in hay for k in keywords):
            return True
        return lexicon_score(item.get("text", "")) < -0.4

    def detect(self, items):
        cfg = self.effective_config()
        handles = {a.lower().lstrip("@") for a in as_list(cfg["accounts"])}
        if not handles:
            handles = {self.account.lower().lstrip("@")}
        now = datetime.now(timezone.utc)
        window_s = cfg["window_hours"] * 3600
        negatives = []
        for it in items:
            acct = str(it.get("account", "")).lower().lstrip("@")
            if acct not in handles:
                continue
            if (now - _ts(it)).total_seconds() > window_s:
                continue
            if self.is_negative(it, cfg["negative_keywords"]):
                negatives.append(it)
        events = []
        if len(negatives) >= cfg["spike_threshold"]:
            last_alert = self._state.get("last_alert_ts", 0)
            import time
            if time.time() - last_alert >= cfg["alert_cooldown_hours"] * 3600:
                self._state["last_alert_ts"] = time.time()
                sample = " | ".join(str(n.get("text"))[:60] for n in negatives[:3])
                events.append(
                    self.make_event(
                        item_id=f"crisis-{int(time.time())}",
                        kind="crisis:spike",
                        summary=(f"URGENT: {len(negatives)} negative mentions of "
                                 f"@{sorted(handles)[0]} in the last {cfg['window_hours']}h: "
                                 f"{sample}"),
                        data={"count": len(negatives),
                              "items": negatives[:10]},
                        severity="urgent",
                    )
                )
        return events
