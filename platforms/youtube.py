"""YouTube adapter spec."""

from .base import AdapterSpec

ADAPTER = AdapterSpec(
    name="youtube",
    display="YouTube",
    auth="Browser session sign-in, or official YouTube Data API v3 with OAuth 2.0 "
         "(quota-based, 10,000 units/day default).",
    readable=[
        "Subscriptions feed, search, trending",
        "Channel pages: uploads, subscriber counts, video metadata",
        "Video comments (API commentThreads.list or browser)",
        "Notifications (browser)",
    ],
    postable=[
        "Upload videos via API (videos.insert, quota-expensive) or browser (YouTube Studio)",
        "Comment, reply, like (API with OAuth or browser)",
    ],
    not_possible=[
        "Data API default quota is small; comment-heavy polling burns it fast.",
        "No API for Shorts-specific creation flows; use Studio/browser.",
        "Community posts need channel eligibility.",
    ],
    rate_note="Respect the 10k units/day default quota; cache aggressively and poll slowly.",
    docs=[
        "https://developers.google.com/youtube/v3",
        "https://developers.google.com/youtube/v3/docs/commentThreads/list",
    ],
)
