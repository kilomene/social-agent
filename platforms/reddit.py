"""Reddit adapter spec."""

from .base import AdapterSpec

ADAPTER = AdapterSpec(
    name="reddit",
    display="Reddit",
    auth="Browser session sign-in, or official Reddit API with OAuth 2.0 "
         "(script/app type; free tier has rate limits).",
    readable=[
        "Subreddits: hot/new/top listings, search",
        "Posts, comment trees, user profiles, karma",
        "Inbox: messages, comment replies, mentions (API or browser)",
    ],
    postable=[
        "Submit posts/comments via API (OAuth) or browser",
        "Upvote, save, follow users/subreddits",
        "DMs (chat) via browser; API chat support is limited",
    ],
    not_possible=[
        "API rate limits are strict for free apps (60 req/min); poll slowly.",
        "Many subreddits require karma/age minimums — automation gets filtered.",
        "Mod actions need moderator permissions.",
    ],
    rate_note="60 requests/minute on the free API tier; browser polling should be gentler still.",
    docs=[
        "https://www.reddit.com/dev/api/",
        "https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-API-Terms",
    ],
)
