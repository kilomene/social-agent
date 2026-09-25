""" linkedin platform package: adapter spec + watchers + workspace.

Subpackages: watchers/ (engine registration), memory/ (shared-DB
view), workspace/ (per-platform runtime state). The ADAPTER spec
below is the declarative no-API capability description: this package
only describes what the platform supports; live execution happens
via execution tickets fulfilled by the external agent visibly in its own browser
(docs/HOST_BROWSER.md). The repo drives no browser itself.
"""

"""LinkedIn adapter spec — no APIs.

social-agent never touches LinkedIn via an API (no API client, no API
key, no API backend) and drives no browser itself. Approved actions
become execution tickets fulfilled visibly by the external agent in its own
Chromium (docs/HOST_BROWSER.md); credentials stay in the host's
Secure Vault.
"""

from ..base import AdapterSpec

ADAPTER = AdapterSpec(
    name="linkedin",
    display="LinkedIn",
    auth="Sign-in in the external agent's own live browser (vault-backed "
         "browser flow with the user's approval, completing any "
         "verification challenge with the user). No credentials stored "
         "by social-agent — logins live only in the secure vault.",
    readable=[
        "Home feed (browser scroll)",
        "Profiles, connection counts, experience sections",
        "Company pages: posts, follower counts",
        "Post pages: reactions, comments, repost counts",
        "Notifications (mentions, reactions, comments, follows)",
        "Messaging threads (browser)",
    ],
    postable=[
        "Post text updates, reply, repost, react (browser)",
        "Messages via browser (throttled, consent-aware)",
    ],
    not_possible=[
        "LinkedIn's User Agreement prohibits scraping and unauthorized "
        "automation; browser-driven data collection is prohibited by "
        "default and fails closed — it proceeds only with the explicit "
        "tos.acknowledged_risk opt-in (restriction risk logged).",
        "Bulk messaging / connection blasts are out of scope (spam).",
        "No API access: the owner ordered browser-only on every platform.",
    ],
    rate_note="LinkedIn enforces weekly invitation limits and behavioral "
              "throttles in-app; stay conservative — low volume, human "
              "pacing, business hours.",
    docs=[
        "https://www.linkedin.com/legal/user-agreement",
        "https://www.linkedin.com/legal/professional-community-policies",
    ],
)
