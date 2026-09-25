"""Central rate-limit controller: token buckets per (platform, action).

Every acting path (engage like/comment/follow, moderate hide, post/publish)
checks the controller FIRST via :func:`check`: allowed -> consume + log;
denied -> the caller queues the action with ``rate_limited`` status and a
``retry_at`` timestamp. Actions are never silently dropped and buckets are
never exceeded.

Config: policy.yaml -> rate_limits. Per-action overrides are supported:
  rate_limits:
    tiktok:
      actions_per_hour: 10
      actions_per_day: 40
      like: {per_hour: 30, per_day: 200}   # overrides for this action
      comment: {per_hour: 20, per_day: 100}
Missing entries fall back to the platform caps, then the default caps.

Backoff: consecutive denials on one bucket widen the retry window
exponentially (capped at 24h); a successful consume resets the denial count.
"""
