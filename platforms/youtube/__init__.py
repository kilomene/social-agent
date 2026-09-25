""" youtube platform package: adapter spec + watchers + workspace.

Subpackages: watchers/ (engine registration), memory/ (shared-DB
view), workspace/ (per-platform runtime state). The ADAPTER spec
below is the declarative no-API capability description: this package
only describes what the platform supports; live execution happens
via execution tickets fulfilled by the external agent visibly in its own browser
(docs/HOST_BROWSER.md). The repo drives no browser itself.
"""

"""YouTube adapter spec — no APIs.

social-agent never touches YouTube via an API (no API client, no API
key, no API backend) and drives no browser itself. Approved actions
become execution tickets fulfilled visibly by the external agent in its own
Chromium (docs/HOST_BROWSER.md); credentials stay in the host's
Secure Vault.
"""

from ..base import AdapterSpec

ADAPTER = AdapterSpec(
    name="youtube",
    display="YouTube",
    auth="Sign-in in the external agent's own live browser (vault-backed "
         "browser flow with the user's approval). No credentials stored "
         "by social-agent — logins live only in the secure vault.",
    readable=[
        "Subscriptions feed, search, trending (browser)",
        "Channel pages: uploads, subscriber counts, video metadata",
        "Video comments (browser)",
        "Notifications (browser)",
    ],
    postable=[
        "Upload videos via browser (YouTube Studio)",
        "Comment, reply, like (browser)",
    ],
    not_possible=[
        "Nothing that artificially inflates views, likes, comments, or "
        "subscribers — refused (fake engagement).",
        "Community posts need channel eligibility.",
    ],
    rate_note="Keep actions low-volume and human-paced; aggressive "
              "automation risks the channel.",
    docs=[
        "https://www.youtube.com/t/terms",
    ],
)
