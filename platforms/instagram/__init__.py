""" instagram platform package: adapter spec + watchers + workspace.

Subpackages: watchers/ (engine registration), memory/ (shared-DB
view), browser_profile/ (pointer to the shared identity profile),
workspace/ (per-platform runtime state). The ADAPTER spec below is
the declarative browser-only capability description.
"""

"""Instagram adapter spec — browser-only.

social-agent drives Instagram exclusively through the account's persistent
browser session. There is no API client, no API key, and no API backend.
"""

from ..base import AdapterSpec

ADAPTER = AdapterSpec(
    name="instagram",
    display="Instagram",
    auth="Browser session sign-in in the persistent profile "
         "(headed first login; the human signs in). No credentials stored "
         "by social-agent.",
    readable=[
        "Feed, Reels, Explore, hashtags, locations (browser)",
        "Profiles, follower counts, posts, comments",
        "Notifications and inbox (browser)",
    ],
    postable=[
        "Post photos/Reels via browser",
        "Like, comment, follow, DM (browser)",
    ],
    not_possible=[
        "Story stickers/interactive elements need the native app.",
        "Aggressive automation triggers action blocks quickly — "
        "low volume with human-like pauses only.",
    ],
    rate_note="Instagram action-blocks aggressively; keep likes/comments/follows low per hour with human-like pauses.",
    docs=[
        "https://help.instagram.com/termsofuse",
    ],
)
