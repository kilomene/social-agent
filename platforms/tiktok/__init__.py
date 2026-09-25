""" tiktok platform package: adapter spec + watchers + workspace.

Subpackages: watchers/ (engine registration), memory/ (shared-DB
view), browser_profile/ (pointer to the shared identity profile),
workspace/ (per-platform runtime state). The ADAPTER spec below is
the declarative browser-only capability description.
"""

"""TikTok adapter spec — browser-only.

social-agent drives TikTok exclusively through the account's persistent
browser session. There is no API client, no API key, and no API backend.
"""

from ..base import AdapterSpec

ADAPTER = AdapterSpec(
    name="tiktok",
    display="TikTok",
    auth="Browser session sign-in (email/phone/username + password, or QR). "
         "No credentials stored by social-agent.",
    readable=[
        "For You / Following feed (scroll)",
        "Profile pages: videos, follower counts, bio",
        "Video pages: captions, comments, like counts",
        "Inbox notifications (likes, comments, follows, mentions)",
        "DM threads (read)",
    ],
    postable=[
        "Upload video (via tiktok.com/upload in browser)",
        "Like, comment, follow, share, save (browser)",
    ],
    not_possible=[
        "DM sending at scale is throttled by TikTok and may trigger verification.",
        "Private/friends-only content is not visible without that relationship.",
    ],
    rate_note="Keep acting well under ~10 actions/hour; new accounts are throttled harder.",
    docs=[
        "https://www.tiktok.com/legal/page/us/terms-of-service/en",
    ],
)
