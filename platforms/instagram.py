"""Instagram adapter spec."""

from .base import AdapterSpec

ADAPTER = AdapterSpec(
    name="instagram",
    display="Instagram",
    auth="Browser session sign-in. Official API (Meta) covers business/creator "
         "accounts for publishing and comment management.",
    readable=[
        "Feed, Reels, Explore, hashtags, locations",
        "Profiles, follower counts, posts, comments",
        "Notifications and inbox (browser)",
    ],
    postable=[
        "Post photos/Reels via browser; business accounts can publish via Content Publishing API",
        "Like, comment, follow, DM (browser)",
    ],
    not_possible=[
        "Personal accounts have no official write API — browser-driven only.",
        "Story posting via API is limited; stickers/interactive elements need the app.",
        "Aggressive automation triggers action blocks quickly.",
    ],
    rate_note="Instagram action-blocks aggressively; keep likes/comments/follows low per hour with human-like pauses.",
    docs=[
        "https://developers.facebook.com/docs/instagram-platform/",
        "https://developers.facebook.com/docs/instagram-platform/content-publishing",
    ],
)
