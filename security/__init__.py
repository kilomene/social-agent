"""Security-conscious behavior for the social agent.

Hard rules (enforced in code, examined in exams):
  * The agent NEVER asks for, accepts, or writes passwords, API keys, tokens,
    or private keys into content, drafts, logs, or state. `post draft` and
    `engage comment` refuse text matching secret patterns (see secrets.py).
  * No credentials are ever stored in the repo or state dir (existing rule,
    re-asserted here).
  * Suspicious account activity (follower purges, unknown sessions) fires
    urgent events via the security watcher (watchers/security_watcher.py).
"""
