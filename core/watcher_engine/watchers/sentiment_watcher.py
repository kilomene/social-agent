"""Sentiment watcher: scores sentiment of comments/mentions about your accounts.

Items: {"id", "account" (your handle), "text", "sentiment" (-1..1, optional),
        "author"}. When an item has no sentiment score, a small built-in
lexicon scores it (stdlib, no models). Emits an event on significant
sentiment shifts per account (rolling window average vs previous window).
"""

from ..framework import Watcher, as_list

POSITIVE = {"love", "amazing", "great", "awesome", "best", "fire", "goat",
            "incredible", "perfect", "brilliant", "thanks", "thank", "helpful",
            "good", "excellent", "obsessed", "iconic"}
NEGATIVE = {"hate", "terrible", "awful", "worst", "trash", "scam", "fake",
            "boring", "cringe", "disappointing", "bad", "horrible", "mid",
            "overrated", "annoying", "stupid"}


def lexicon_score(text):
    words = [w.strip(".,!?;:\"'()").lower() for w in (text or "").split()]
    pos = sum(1 for w in words if w in POSITIVE)
    neg = sum(1 for w in words if w in NEGATIVE)
    if pos == neg == 0:
        return 0.0
    return (pos - neg) / max(pos + neg, 1)


class SentimentWatcher(Watcher):
    type = "sentiment"
    description = "Tracks sentiment about your accounts; alerts on significant shifts."
    schema = {
        "required": [],
        "optional": {
            "watched_accounts": [],
            "window_size": 20,
            "shift_threshold": 0.35,
        },
    }

    def detect(self, items):
        cfg = self.effective_config()
        watched = {a.lower().lstrip("@") for a in as_list(cfg["watched_accounts"])}
        if not watched:
            watched = {self.account.lower().lstrip("@")}
        windows = self._state.setdefault("windows", {})
        events = []
        for it in items:
            acct = str(it.get("account", "")).lower().lstrip("@")
            if acct not in watched:
                continue
            s = it.get("sentiment")
            if not isinstance(s, (int, float)):
                s = lexicon_score(it.get("text", ""))
            win = windows.setdefault(acct, [])
            prev_avg = sum(win) / len(win) if win else None
            win.append(float(s))
            win[:] = win[-cfg["window_size"]:]
            if prev_avg is None or len(win) < 3:
                continue
            new_avg = sum(win) / len(win)
            if abs(new_avg - prev_avg) >= cfg["shift_threshold"]:
                direction = "up" if new_avg > prev_avg else "down"
                events.append(
                    self.make_event(
                        item_id=f"{it.get('id')}-shift",
                        kind="sentiment:shift",
                        summary=(f"sentiment for @{acct} shifted {direction}: "
                                 f"{prev_avg:+.2f} -> {new_avg:+.2f} "
                                 f"(triggered by @{it.get('author', '?')})"),
                        data={"account": acct, "prev_avg": round(prev_avg, 3),
                              "new_avg": round(new_avg, 3), "item": it},
                        severity="warning" if direction == "down" else "info",
                    )
                )
        return events
