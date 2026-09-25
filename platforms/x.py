"""X (Twitter) adapter spec."""

from .base import AdapterSpec

ADAPTER = AdapterSpec(
    name="x",
    display="X (Twitter)",
    auth="Browser session sign-in, or official X API v2 with OAuth 2.0 (user context). "
         "API tiers are paid; free tier is read/write-limited.",
    readable=[
        "Home timeline, search, hashtags, lists",
        "Profiles, follower counts, tweets, replies",
        "Notifications (mentions, likes, reposts, follows)",
        "DMs (via API with elevated access, or browser)",
    ],
    postable=[
        "Post tweets, reply, repost, quote, like, bookmark (browser or API)",
        "DMs via API (user context) or browser",
    ],
    not_possible=[
        "Free API tier cannot do meaningful volume; check current pricing.",
        "Scraping at scale violates the ToS; use the official API for bulk reads.",
        "Polls/ads management need separate API products.",
    ],
    rate_note="X enforces aggressive per-15-min windows on the API and behavioral limits in-app; stay conservative.",
    docs=[
        "https://docs.x.com/x-api/introduction",
        "https://docs.x.com/x-api/posts/creation",
    ],
)
