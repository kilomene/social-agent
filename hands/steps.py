"""Step templates: human-readable browser instructions for the external agent.

Each execution ticket carries a ``steps`` list — plain-language
instructions the external agent follows visibly in its own browser
(live browser card the user watches). No selectors, no automation
code: the external agent sees the page and acts like the account owner.

Every template ends with the login-wall rule: the host browser is the
user's own live logged-in session. If a login screen appears, STOP —
never type passwords or 2FA codes; sign-in goes through the vault-backed
browser flow with the user's approval.
"""

PLATFORM_HOME = {
    "tiktok": "https://www.tiktok.com/",
    "x": "https://x.com/",
    "instagram": "https://www.instagram.com/",
    "facebook": "https://www.facebook.com/",
    "youtube": "https://www.youtube.com/",
    "reddit": "https://www.reddit.com/",
    "linkedin": "https://www.linkedin.com/",
}

LOGIN_WALL_STEP = (
    "Login check FIRST: if you land on a login / sign-in / checkpoint screen "
    "instead of the content, STOP. Do not type any password, 2FA code, or "
    "recovery detail. Logins live in the agent's secure vault (or the "
    "user's own browser) — sign-in happens only through the vault-backed "
    "browser flow with the user's approval. Record what you saw as evidence "
    "and leave the ticket unfulfilled."
)

EVIDENCE_STEP = (
    "Record evidence: what you did, what you saw (timestamps, URLs, counts), "
    "and anything unexpected. Evidence is attached to the ticket on fulfill."
)

_T = {
    "like": [
        "Open the target in your live Chromium: {target_url}",
        LOGIN_WALL_STEP,
        "Wait for the post/video to load, then click the Like (heart) button once.",
        "Confirm the like registered (heart filled / count incremented).",
        EVIDENCE_STEP,
    ],
    "comment": [
        "Open the target in your live Chromium: {target_url}",
        LOGIN_WALL_STEP,
        "Open the comment box and type exactly this comment (do not improvise):",
        ">>> {text}",
        "Post the comment and confirm it appears under your account's name.",
        EVIDENCE_STEP,
    ],
    "follow": [
        "Open the profile in your live Chromium: {target_url}",
        LOGIN_WALL_STEP,
        "Click Follow once and confirm the button changes to Following.",
        EVIDENCE_STEP,
    ],
    "unfollow": [
        "Open the profile in your live Chromium: {target_url}",
        LOGIN_WALL_STEP,
        "Click Following/Unfollow once, confirm the dialog, and confirm the "
        "button reverts to Follow.",
        EVIDENCE_STEP,
    ],
    "post_text": [
        "In your live Chromium, open {platform_home} and start a new post.",
        LOGIN_WALL_STEP,
        "Type exactly this text (do not improvise):",
        ">>> {text}",
        "Publish and confirm the post appears on the account's profile/feed.",
        EVIDENCE_STEP,
    ],
    "post_video": [
        "In your live Chromium, open {platform_home} and start a new video upload.",
        LOGIN_WALL_STEP,
        "Upload the file at: {file}",
        "Set the caption to exactly this (do not improvise):",
        ">>> {text}",
        "Publish and confirm the video appears on the account's profile/feed.",
        EVIDENCE_STEP,
    ],
    "post_photo": [
        "In your live Chromium, open {platform_home} and start a new photo post.",
        LOGIN_WALL_STEP,
        "Upload the file at: {file}",
        "Set the caption to exactly this (do not improvise):",
        ">>> {text}",
        "Publish and confirm the post appears on the account's profile/feed.",
        EVIDENCE_STEP,
    ],
    "dm_send": [
        "In your live Chromium, open the conversation: {target_url}",
        LOGIN_WALL_STEP,
        "Type exactly this message (do not improvise):",
        ">>> {text}",
        "Send it and confirm it appears in the thread as sent.",
        EVIDENCE_STEP,
    ],
    "hide_comment": [
        "In your live Chromium, open the post containing the comment: {target_url}",
        LOGIN_WALL_STEP,
        "Find the comment matching: {text}",
        "Hide/delete it using the platform's own controls (your own post only).",
        "Confirm the comment is no longer visible to others.",
        EVIDENCE_STEP,
    ],
    "reshare": [
        "Open the target in your live Chromium: {target_url}",
        LOGIN_WALL_STEP,
        "Use the platform's repost/share control once (no quote-text unless the "
        "plan says so).",
        "Confirm the reshare appears on the account's profile.",
        EVIDENCE_STEP,
    ],
    "subscribe": [
        "Open the channel in your live Chromium: {target_url}",
        LOGIN_WALL_STEP,
        "Click Subscribe once and confirm it changes to Subscribed.",
        EVIDENCE_STEP,
    ],
    "profile_update": [
        "In your live Chromium, open the account's profile edit page on {platform}.",
        LOGIN_WALL_STEP,
        "Apply exactly these changes (nothing else): {text}",
        "Save and confirm the profile shows the changes.",
        EVIDENCE_STEP,
    ],
}


def build_steps(action, platform, params):
    """Render the step list for an action. Missing params degrade gracefully."""
    params = params or {}
    tpl = _T.get(action, _T["like"])
    ctx = {
        "target_url": params.get("target_url") or params.get("target")
                        or params.get("url") or "(see plan summary)",
        "text": params.get("text") or params.get("comment")
                or params.get("caption") or "(see plan summary)",
        "file": params.get("file") or params.get("video_path")
                or params.get("photo_path") or "(see plan summary)",
        "platform": platform,
        "platform_home": PLATFORM_HOME.get(platform, ""),
    }
    return [s.format(**ctx) for s in tpl]


def supported_actions():
    return sorted(_T)
