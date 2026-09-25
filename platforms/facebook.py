"""Facebook adapter spec."""

from .base import AdapterSpec

ADAPTER = AdapterSpec(
    name="facebook",
    display="Facebook",
    auth="Browser session sign-in. Pages can use the official Graph API with a "
         "Page access token (app review may be required).",
    readable=[
        "News Feed, Pages, Groups (member-visible), Watch",
        "Page posts, comments, reactions, follower counts",
        "Page inbox / Messenger (Page scope)",
    ],
    postable=[
        "Page posts, comments, replies via Graph API (Page token)",
        "Personal profile actions are browser-driven only",
    ],
    not_possible=[
        "No official API for personal-profile posting — browser only.",
        "Group content requires membership and respects group privacy.",
        "Marketplace automation is out of scope.",
    ],
    rate_note="Graph API has per-app/per-page rate limits; browser actions on profiles are throttled behaviorally.",
    docs=[
        "https://developers.facebook.com/docs/pages-api/",
        "https://developers.facebook.com/docs/graph-api/",
    ],
)
