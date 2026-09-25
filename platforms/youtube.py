"""YouTube adapter spec — browser-only.

social-agent drives YouTube exclusively through the account's persistent
browser session. There is no API client, no API key, and no API backend.
"""

from .base import AdapterSpec

ADAPTER = AdapterSpec(
    name="youtube",
    display="YouTube",
    auth="Browser session sign-in in the persistent profile "
         "(headed first login; the human signs in). No credentials stored "
         "by social-agent.",
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
