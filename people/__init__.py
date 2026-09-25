"""People memory database: remember recurring followers & conversations.

Per-account store: <home>/people/<account>.json mapping a lower-cased handle
to a record:
  {handle, first_seen, last_seen,
   counts: {comment, like, dm, follow, mention},
   sentiments: [recent -1..1 scores],
   notes: [{ts, text}], tags: [...],
   conversations: [{ts, kind, summary}]}

Fed by watcher events (via the `listen` command — watchers themselves stay
read-only). Tags like ``top-fan`` / ``collaborator`` / ``troll`` drive
prioritization; top-fan authors get a small interest-score boost in
engagement (see engagement/interest.py score_user tags param).
"""
