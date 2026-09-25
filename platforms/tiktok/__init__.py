""" tiktok platform package: adapter spec + watchers + workspace.

Subpackages: watchers/ (engine registration), memory/ (shared-DB
view), workspace/ (per-platform runtime state). The ADAPTER spec
below is the declarative no-API capability description: this package
only describes what the platform supports; live execution happens
via execution tickets fulfilled by the external agent visibly in its own browser
(docs/HOST_BROWSER.md). The repo drives no browser itself.
"""

"""TikTok adapter spec — no APIs.

social-agent never touches TikTok via an API (no API client, no API
key, no API backend) and drives no browser itself. Approved actions
become execution tickets fulfilled visibly by the external agent in its own
Chromium (docs/HOST_BROWSER.md); credentials stay in the host's
Secure Vault.
"""

from ..base import AdapterSpec

ADAPTER = AdapterSpec(
    name="tiktok",
    display="TikTok",
    auth="Sign-in in the external agent's own live browser (vault-backed "
         "browser flow with the user's approval). No credentials stored "
         "by social-agent — logins live only in the secure vault.",
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
