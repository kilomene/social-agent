""" instagram platform package: adapter spec + watchers + workspace.

Subpackages: watchers/ (engine registration), memory/ (shared-DB
view), workspace/ (per-platform runtime state). The ADAPTER spec
below is the declarative no-API capability description: this package
only describes what the platform supports; live execution happens
via execution tickets fulfilled by the external agent visibly in its own browser
(docs/HOST_BROWSER.md). The repo drives no browser itself.
"""

"""Instagram adapter spec — no APIs.

social-agent never touches Instagram via an API (no API client, no API
key, no API backend) and drives no browser itself. Approved actions
become execution tickets fulfilled visibly by the external agent in its own
Chromium (docs/HOST_BROWSER.md); credentials stay in the host's
Secure Vault.
"""

from ..base import AdapterSpec

ADAPTER = AdapterSpec(
    name="instagram",
    display="Instagram",
    auth="Sign-in in the external agent's own live browser (vault-backed "
         "browser flow with the user's approval). No credentials stored "
         "by social-agent — logins live only in the secure vault.",
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
