"""TikTok DM adapter: REFUSES by design.

Reason (verified 2026-09-25): TikTok DM conversation content is app-only.
The web client shows that a conversation exists (unread badge) but the
message bodies are not readable in the browser — the host agent confirmed
live that TikTok DMs require the phone app. A DM agent that pretended to
read TikTok DMs would be fabricating observations, so this adapter parks
TikTok instead of pretending: readiness() returns False with the documented
reason, and any tick/report call for tiktok refuses cleanly.

If TikTok ever exposes DM content on web, flip STATUS to "ready" and
implement check_steps()/normalize() like platforms/x.py.
"""

PLATFORM = "tiktok"
STATUS = "refused"

REFUSAL_REASON = (
    "TikTok DM message content is app-only and not visible in the web "
    "client (verified live 2026-09-25: conversation list shows unread "
    "badges but message bodies require the phone app). The DM agent parks "
    "TikTok rather than pretending to read DMs."
)


class TikTokDMRefused(Exception):
    """Raised whenever the TikTok DM path is invoked."""


def readiness():
    return False, REFUSAL_REASON


def check_steps(account, threads):
    raise TikTokDMRefused(REFUSAL_REASON)


def normalize(raw):
    raise TikTokDMRefused(REFUSAL_REASON)
