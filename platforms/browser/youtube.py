"""YouTube browser recipe (no API)."""

LAST_VERIFIED = "2026-09-25"
HOME_URL = "https://www.youtube.com/"
STUDIO_URL = "https://studio.youtube.com/"

LOGIN_NOTES = (
    "Login goes through Google accounts (accounts.google.com). 2-step "
    "verification challenges are common — the human completes them in the "
    "headed window. After login, YouTube Studio is the upload surface."
)

SELECTORS = {
    "like": 'ytd-toggle-button-renderer #button[aria-label*="like this video"]',
    "comment_box": '#placeholder-area',
    "comment_input": '#contenteditable-root',
    "comment_submit": '#submit-button',
    "subscribe": 'ytd-subscribe-button-renderer button',
    "unsubscribe": 'ytd-subscribe-button-renderer button',
    "upload_button": 'ytd-topbar-menu-button-renderer button[aria-label="Create"]',
    "upload_video_item": 'ytcp-text-menu',
    "upload_input": 'input[type="file"][accept*="video"]',
    "upload_title": '#textbox',
    "upload_next": '#next-button',
    "upload_publish": '#done-button',
    "notifications_bell": 'ytd-notification-topbar-button-renderer button',
}

QUIRKS = (
    "Like/dislike live under the player; the comment box needs a click on "
    "the placeholder before the editable appears. Uploads go through "
    "YouTube Studio's multi-step dialog (details → visibility → publish) — "
    "the recipe walks it with Next/Publish. Shorts upload from the same "
    "dialog; vertical video is auto-classified as a Short."
)


def _s(name):
    return SELECTORS[name]


def like(target_url):
    return [("goto", {"url": target_url}), ("click", {"selector": _s("like")})]


def comment(target_url, text):
    return [("goto", {"url": target_url}),
            ("click", {"selector": _s("comment_box")}),
            ("fill", {"selector": _s("comment_input"), "text": text}),
            ("click", {"selector": _s("comment_submit")})]


def subscribe(channel_url):
    return [("goto", {"url": channel_url}),
            ("click", {"selector": _s("subscribe")})]


def upload_video(video_path, title="", description=""):
    steps = [("goto", {"url": STUDIO_URL}),
             ("click", {"selector": _s("upload_button")}),
             ("upload", {"selector": _s("upload_input"), "file": video_path}),
             ("wait_for", {"selector": _s("upload_title")})]
    if title:
        steps.append(("fill", {"selector": _s("upload_title"), "text": title}))
    steps += [("click", {"selector": _s("upload_next")}),
              ("click", {"selector": _s("upload_next")}),
              ("click", {"selector": _s("upload_publish")})]
    return steps


ACTIONS = {"like": like, "comment": comment, "subscribe": subscribe,
           "upload_video": upload_video}
