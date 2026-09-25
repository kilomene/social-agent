""" linkedin platform package: adapter spec + watchers + workspace.

Subpackages: watchers/ (engine registration), memory/ (shared-DB
view), browser_profile/ (pointer to the shared identity profile),
workspace/ (per-platform runtime state). The ADAPTER spec below is
the declarative browser-only capability description.
"""

"""LinkedIn adapter spec — browser-only.

social-agent drives LinkedIn exclusively through the account's persistent
browser session. There is no API client, no API key, and no API backend.
"""

from ..base import AdapterSpec

ADAPTER = AdapterSpec(
    name="linkedin",
    display="LinkedIn",
    auth="Browser session sign-in in the persistent profile "
         "(headed first login; the human signs in, completes any "
         "verification challenge). No credentials stored by social-agent.",
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
