"""TikTok adapter spec."""

from .base import AdapterSpec

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
        "Content Posting API (for approved developer apps: video.upload / video.publish scopes)",
        "Like, comment, follow, share, save",
    ],
    not_possible=[
        "No public write API for ordinary personal accounts; posting is browser-driven unless you register an approved app.",
        "DM sending at scale is throttled by TikTok and may trigger verification.",
        "Private/friends-only content is not visible without that relationship.",
    ],
    rate_note="Keep acting well under ~10 actions/hour; new accounts are throttled harder.",
    docs=[
        "https://developers.tiktok.com/doc/login-kit-web/",
        "https://developers.tiktok.com/doc/content-posting-api-get-started",
        "https://developers.tiktok.com/doc/display-api-overview",
    ],
)
