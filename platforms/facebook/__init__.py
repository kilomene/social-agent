""" facebook platform package: adapter spec + watchers + workspace.

Subpackages: watchers/ (engine registration), memory/ (shared-DB
view), workspace/ (per-platform runtime state). The ADAPTER spec
below is the declarative no-API capability description: this package
only describes what the platform supports; live execution happens
via execution tickets fulfilled by the external agent visibly in its own browser
(docs/HOST_BROWSER.md). The repo drives no browser itself.
"""

"""Facebook adapter spec — no APIs.

social-agent never touches Facebook via an API (no API client, no API
key, no API backend) and drives no browser itself. Approved actions
become execution tickets fulfilled visibly by the external agent in its own
Chromium (docs/HOST_BROWSER.md); credentials stay in the host's
Secure Vault.
"""

from ..base import AdapterSpec

ADAPTER = AdapterSpec(
    name="facebook",
    display="Facebook",
    auth="Sign-in in the external agent's own live browser (vault-backed "
         "browser flow with the user's approval). No credentials stored "
         "by social-agent — logins live only in the secure vault.",
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
