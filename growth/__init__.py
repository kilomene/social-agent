"""Growth engine: organic, ToS-compliant account growth.

Submodules:
  strategy  per-platform growth playbooks (cadence, pillars, loops, CTAs)
  goals     follower/milestone goal tracking
  audit     account growth audit across scored pillars
  youtube   YouTube deep support (preflight, titles, descriptions, thumbnails)

Guard order: growth tactics sit UNDER the platform ToS layer. A tactic that
would violate a platform's terms is refused by platforms/tos.py before any
growth logic runs — growth can never override ToS, missions, or approvals.
"""
