""" facebook platform package: adapter spec + watchers + workspace.

Subpackages: watchers/ (engine registration), memory/ (shared-DB
view), browser_profile/ (pointer to the shared identity profile),
workspace/ (per-platform runtime state). The ADAPTER spec below is
the declarative browser-only capability description.
"""

"""Facebook adapter spec — browser-only.

social-agent drives Facebook exclusively through the account's persistent
browser session. There is no API client, no API key, and no API backend.
"""

from ..base import AdapterSpec

ADAPTER = AdapterSpec(
    name="facebook",
    display="Facebook",
    auth="Browser session sign-in in the persistent profile "
         "(headed first login; the human signs in). No credentials stored "
         "by social-agent.",
    readable=[
        "News Feed, Pages, Groups (member-visible), Watch (browser)",
        "Page posts, comments, reactions, follower counts",
        "Page inbox / Messenger (Page scope)",
    ],
    postable=[
        "Page posts, comments, replies (browser)",
        "Personal profile actions (browser)",
    ],
    not_possible=[
        "Meta's terms restrict automated data collection; bulk or scripted "
        "actions are refused — genuine, human-directed, low-volume only.",
        "Group content requires membership and respects group privacy.",
        "Marketplace automation is out of scope.",
    ],
    rate_note="Keep browser actions on profiles low-volume with human-like "
              "pauses; Meta throttles aggressively.",
    docs=[
        "https://www.facebook.com/terms.php",
    ],
)
