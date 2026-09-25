"""Unified human approval queue.

Every acting operation that needs a human decision — proposed likes,
comments, follows, hide requests, video posts, publishes, reply drafts —
lives in ONE queue (``<home>/approvals/pending.json``) instead of being
scattered across engagement/moderation/post state files.

Per-action-type policy lives in ``policy.yaml`` -> ``approvals.per_type``:
``require`` (human must approve; the safe default) or ``auto`` (act
immediately, still logged). Anything not listed defaults to ``require``.

Statuses: pending | approved | rejected | done | expired | held | rate_limited
  * held:       parked by crisis mode; re-pended when crisis ends.
  * rate_limited: the action hit a rate bucket; retry after ``retry_at``.
"""
