""" x platform package: adapter spec + watchers + workspace.

Subpackages: watchers/ (engine registration), memory/ (shared-DB
view), workspace/ (per-platform runtime state). The ADAPTER spec
below is the declarative no-API capability description: this package
only describes what the platform supports; live execution happens
via execution tickets fulfilled by the external agent visibly in its own browser
(docs/HOST_BROWSER.md). The repo drives no browser itself.
"""

"""X (Twitter) adapter spec — no APIs.

social-agent never touches X via an API (no API client, no API
key, no API backend) and drives no browser itself. Approved actions
become execution tickets fulfilled visibly by the external agent in its own
Chromium (docs/HOST_BROWSER.md); credentials stay in the host's
Secure Vault.
"""

from ..base import AdapterSpec

ADAPTER = AdapterSpec(
    name="x",
    display="X (Twitter)",
    auth="Sign-in in the external agent's own live browser (vault-backed "
         "browser flow with the user's approval). No credentials stored "
         "by social-agent — logins live only in the secure vault.",
    readable=[
        "Home timeline, search, hashtags, lists (browser scroll)",
        "Profiles, follower counts, tweets, replies",
        "Notifications (mentions, likes, reposts, follows)",
        "DMs (browser)",
    ],
    postable=[
        "Post tweets, reply, repost, quote, like, bookmark (browser)",
        "DMs via browser",
    ],
    not_possible=[
        "X's terms require API-only automation; browser-driven engagement "
        "is prohibited by default and fails closed — it proceeds only with "
        "the explicit tos.acknowledged_risk opt-in (suspension risk logged).",
        "Polls/ads management are out of scope.",
    ],
    rate_note="X enforces behavioral limits in-app; stay conservative — "
              "low volume, human pacing.",
    docs=[
        "https://help.x.com/en/rules-and-policies/xrules",
    ],
)
