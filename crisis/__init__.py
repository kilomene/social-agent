"""Crisis mode: global kill switch for all acting operations.

`crisis on` pauses EVERYTHING that acts (posts, likes, comments, follows,
hides, publishes, scheduled renders) while watchers keep monitoring
read-only. Pending approval-queue items are parked as ``held`` and
re-pended on `crisis off` — nothing is lost, nothing auto-resumes.

Guard order (documented in policy/guardrails.md):
  ToS > crisis > approvals > rate limits > quiet hours
ToS stays the ceiling; crisis sits above everything operational.

The crisis *watcher* only detects negative spikes. Auto-pausing on
detection is opt-in (`auto_pause: true` on the watcher, default off):
a false positive must never be able to silence the account on its own.
"""
