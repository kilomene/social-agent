"""LinkedIn browser recipe (no API).

LinkedIn's DOM changes without notice; prefer role/aria-label selectors
over class chains — they rot slower. LinkedIn aggressively throttles
rapid actions and shows verification challenges on unusual devices; the
persistent profile keeps the session warm and human pacing keeps it safe.
"""

LAST_VERIFIED = "2026-09-25"
HOME_URL = "https://www.linkedin.com/feed/"

LOGIN_NOTES = (
    "Login with email + password in the headed window on first run; "
    "LinkedIn may show an email/phone verification challenge on a new "
    "device — the human completes it. The persistent profile keeps the "
    "session; re-login is rare."
)

SELECTORS = {
    # aria-label based: LinkedIn localizes these; re-verify per locale
    "like": 'button[aria-label*="Like"]',
    "comment_toggle": 'button[aria-label*="Comment"]',
    "comment_box": 'div[role="textbox"]',
    "comment_post": 'button:has-text("Post")',
    "follow": 'button:has-text("Follow")',
    "unfollow": 'button:has-text("Following")',
    "connect": 'button:has-text("Connect")',
    "repost": 'button[aria-label*="Repost"]',
    "composer_toggle": 'button:has-text("Start a post")',
    "composer_box": 'div[role="textbox"]',
    "composer_post": 'button:has-text("Post")',
    "upload_input": 'input[type="file"][accept*="image"]',
    "notifications_bell": 'a[href*="/notifications/"]',
    "dm_thread": 'a[href*="/messaging/thread/"]',
    "dm_box": 'div[role="textbox"]',
    "dm_send": 'button:has-text("Send")',
}

QUIRKS = (
    "LinkedIn throttles connection invites weekly and rate-limits rapid "
    "actions; keep volumes low and human-paced. aria-label selectors are "
    "locale-dependent — re-verify when the account language changes. "
    "Comment boxes and the composer are both role=textbox; scope the "
    "selector to the open dialog. Messaging send requires the thread to "
    "be open and the box focused."
)


def _s(name):
    return SELECTORS[name]


def like(target_url):
    return [("goto", {"url": target_url}),
            ("click", {"selector": _s("like")})]


def comment(target_url, text):
    return [("goto", {"url": target_url}),
            ("click", {"selector": _s("comment_toggle")}),
            ("fill", {"selector": _s("comment_box"), "text": text}),
            ("click", {"selector": _s("comment_post")})]


def follow(profile_url):
    return [("goto", {"url": profile_url}),
            ("click", {"selector": _s("follow")})]


def unfollow(profile_url):
    return [("goto", {"url": profile_url}),
            ("click", {"selector": _s("unfollow")})]


def connect(profile_url, note=""):
    steps = [("goto", {"url": profile_url}),
             ("click", {"selector": _s("connect")})]
    if note:
        steps.append(("fill", {"selector": _s("comment_box"), "text": note}))
    return steps


def post_text(text):
    return [("goto", {"url": HOME_URL}),
            ("click", {"selector": _s("composer_toggle")}),
            ("fill", {"selector": _s("composer_box"), "text": text}),
            ("click", {"selector": _s("composer_post")})]


def post_photo(photo_path, caption=""):
    steps = [("goto", {"url": HOME_URL}),
             ("click", {"selector": _s("composer_toggle")}),
             ("upload", {"selector": _s("upload_input"), "file": photo_path}),
             ("wait_for", {"selector": _s("composer_box")})]
    if caption:
        steps.append(("fill", {"selector": _s("composer_box"), "text": caption}))
    steps.append(("click", {"selector": _s("composer_post")}))
    return steps


def dm_send(thread_url, text):
    return [("goto", {"url": thread_url}),
            ("fill", {"selector": _s("dm_box"), "text": text}),
            ("click", {"selector": _s("dm_send")})]


ACTIONS = {"like": like, "comment": comment, "follow": follow,
           "unfollow": unfollow, "connect": connect, "post_text": post_text,
           "post_photo": post_photo, "dm_send": dm_send}
