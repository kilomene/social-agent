"""Reddit adapter spec — browser-only.

social-agent drives Reddit exclusively through the account's persistent
browser session. There is no API client, no API key, and no API backend.
"""

from .base import AdapterSpec

ADAPTER = AdapterSpec(
    name="reddit",
    display="Reddit",
    auth="Browser session sign-in in the persistent profile "
         "(headed first login; the human signs in). No credentials stored "
         "by social-agent.",
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
