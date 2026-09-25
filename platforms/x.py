"""X (Twitter) adapter spec — browser-only.

social-agent drives X exclusively through the account's persistent
browser session. There is no API client, no API key, and no API backend.
"""

from .base import AdapterSpec

ADAPTER = AdapterSpec(
    name="x",
    display="X (Twitter)",
    auth="Browser session sign-in in the persistent profile "
         "(headed first login; the human signs in). No credentials stored "
         "by social-agent.",
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
