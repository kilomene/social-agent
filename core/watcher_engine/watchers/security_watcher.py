"""Security watcher: account-anomaly early warning.

Monitors account activity for security-relevant anomalies and fires URGENT
events: sudden follower purges, mass unfollow spikes, and logins from
unknown/new sessions. Read-only — it never touches the account.

Items: {"id", "account", "kind", "timestamp", ...} where kind is one of:
  - "follower_delta": {"followers": int, "prev_followers": int}
  - "session": {"session_id": str, "ip": str, "location": str,
                "known": bool}  (known=false -> unknown session)
  - "unfollow": {"count": int}  (bulk unfollow event)
"""

import time
from datetime import datetime, timezone

from ..framework import Watcher, as_list


def _ts(item):
    try:
        return datetime.fromisoformat(
            str(item.get("timestamp")).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


class SecurityWatcher(Watcher):
    type = "security"
    description = ("Anomaly monitor: follower purges, mass unfollows, "
                   "unknown login sessions.")
    schema = {
        "required": [],
        "optional": {
            "accounts": [],
            "purge_drop_pct": 5,
            "unfollow_spike": 50,
            "window_hours": 24,
            "alert_cooldown_hours": 6,
        },
    }

    def detect(self, items):
        cfg = self.effective_config()
        handles = {a.lower().lstrip("@") for a in as_list(cfg["accounts"])}
        if not handles:
            handles = {self.account.lower().lstrip("@")}
        now = datetime.now(timezone.utc)
        window_s = cfg["window_hours"] * 3600
        events = []

        def cooled(key):
            last = self._state.get(f"last_alert_{key}", 0)
            if time.time() - last < cfg["alert_cooldown_hours"] * 3600:
                return True
            self._state[f"last_alert_{key}"] = time.time()
            return False

        for it in items:
            acct = str(it.get("account", "")).lower().lstrip("@")
            if acct not in handles:
                continue
            if (now - _ts(it)).total_seconds() > window_s:
                continue
            kind = it.get("kind")

            if kind == "follower_delta":
                prev = it.get("prev_followers") or 0
                cur = it.get("followers") or 0
                if prev > 0:
                    drop_pct = (prev - cur) / prev * 100
                    if drop_pct >= cfg["purge_drop_pct"] and not cooled("purge"):
                        events.append(self.make_event(
                            item_id=f"sec-purge-{it.get('id', int(time.time()))}",
                            kind="security:follower_purge",
                            summary=(f"URGENT: @{acct} lost {drop_pct:.1f}% of "
                                     f"followers ({prev} -> {cur}) in the last "
                                     f"{cfg['window_hours']}h. Possible purge, "
                                     f"ban wave, or compromise."),
                            data={"prev": prev, "current": cur,
                                  "drop_pct": round(drop_pct, 1)},
                            severity="urgent",
                        ))

            elif kind == "unfollow":
                count = it.get("count") or 0
                if count >= cfg["unfollow_spike"] and not cooled("unfollow"):
                    events.append(self.make_event(
                        item_id=f"sec-unfollow-{it.get('id', int(time.time()))}",
                        kind="security:unfollow_spike",
                        summary=(f"URGENT: {count} unfollows on @{acct} in the "
                                 f"last {cfg['window_hours']}h (threshold "
                                 f"{cfg['unfollow_spike']}). Check for content "
                                 f"issues or account problems."),
                        data={"count": count},
                        severity="urgent",
                    ))

            elif kind == "session":
                if not it.get("known", True) and not cooled(
                        f"session-{it.get('session_id', 'x')}"):
                    events.append(self.make_event(
                        item_id=f"sec-session-{it.get('id', int(time.time()))}",
                        kind="security:unknown_session",
                        summary=(f"URGENT: new/unknown login session on @{acct}: "
                                 f"{it.get('location', '?')} ({it.get('ip', '?')}). "
                                 f"If this wasn't you: change the password, revoke "
                                 f"sessions, check 2FA now."),
                        data={"session_id": it.get("session_id"),
                              "ip": it.get("ip"), "location": it.get("location")},
                        severity="urgent",
                    ))
        return events
