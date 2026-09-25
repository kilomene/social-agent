"""Threads adapter spec — no APIs.

social-agent never touches Threads via an API (no API client, no API
key, no API backend) and drives no browser itself. Approved actions
become execution tickets fulfilled visibly by the external agent in its own
Chromium (docs/HOST_BROWSER.md); credentials stay in the host's
Secure Vault.

Threads is a Meta text-first conversation app; accounts are tied to
Instagram, so the Instagram session in the live browser usually covers
Threads too.
"""

from ..base import AdapterSpec

ADAPTER = AdapterSpec(
    name="threads",
    display="Threads",
    auth="Sign-in in the external agent's own live browser (vault-backed "
         "browser flow with the user's approval). Threads accounts are tied "
         "to Instagram, so the Instagram session usually covers Threads too. "
         "No credentials stored by social-agent — logins live only in the "
         "secure vault.",
    readable=[
        "Feed (For You / Following), search, topics (browser)",
        "Profiles, follower counts, posts and replies",
        "Notifications and inbox (browser)",
    ],
    postable=[
        "Post text threads via browser",
        "Reply, repost, quote, like, follow, DM (browser)",
    ],
    not_possible=[
        "Meta's terms prohibit unauthorized automation — human-directed, "
        "low-volume, own-account operation only, with human-like pauses.",
        "Threads rate-limits new accounts aggressively — keep volume low.",
    ],
    rate_note="Threads is a Meta property with Instagram-grade automation "
              "detection; keep likes/replies/reposts/follows low per hour "
              "with human-like pauses.",
    docs=[
        "https://help.instagram.com/769983657850450",
    ],
)
