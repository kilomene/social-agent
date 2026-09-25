""" reddit platform package: adapter spec + watchers + workspace.

Subpackages: watchers/ (engine registration), memory/ (shared-DB
view), workspace/ (per-platform runtime state). The ADAPTER spec
below is the declarative no-API capability description: this package
only describes what the platform supports; live execution happens
via execution tickets fulfilled by the external agent visibly in its own browser
(docs/HOST_BROWSER.md). The repo drives no browser itself.
"""

"""Reddit adapter spec — no APIs.

social-agent never touches Reddit via an API (no API client, no API
key, no API backend) and drives no browser itself. Approved actions
become execution tickets fulfilled visibly by the external agent in its own
Chromium (docs/HOST_BROWSER.md); credentials stay in the host's
Secure Vault.
"""

from ..base import AdapterSpec

ADAPTER = AdapterSpec(
    name="reddit",
    display="Reddit",
    auth="Sign-in in the external agent's own live browser (vault-backed "
         "browser flow with the user's approval). No credentials stored "
         "by social-agent — logins live only in the secure vault.",
    readable=[
        "Subreddits: hot/new/top listings, search (browser)",
        "Posts, comment trees, user profiles, karma",
        "Inbox: messages, comment replies, mentions (browser)",
    ],
    postable=[
        "Submit posts/comments via browser",
        "Save, follow users/subreddits (browser)",
        "DMs (chat) via browser",
    ],
    not_possible=[
        "Automated upvoting/downvoting is refused by the CLI "
        "(vote manipulation — ToS prohibition).",
        "Many subreddits require karma/age minimums — automation gets filtered.",
        "Mod actions need moderator permissions.",
    ],
    rate_note="Poll gently and keep actions low-volume; Reddit rate-limits "
              "aggressive behavior.",
    docs=[
        "https://redditinc.com/policies/user-agreement-july-1-2026",
    ],
)
