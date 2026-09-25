"""Instagram browser recipe (no API)."""

LAST_VERIFIED = "2026-09-25"
HOME_URL = "https://www.instagram.com/"

LOGIN_NOTES = (
    "Username + password form. New devices/IPs trigger the checkpoint "
    "challenge ('suspicious login attempt' → email/SMS code). The human "
    "completes the code in the headed window; the agent NEVER touches codes "
    "itself. 'Save login info' prompt appears after first login — accept it "
    "in the headed session so the profile stays signed in."
)

SELECTORS = {
    "like": 'svg[aria-label="Like"]',
    "comment_toggle": 'svg[aria-label="Comment"]',
    "comment_box": 'textarea[aria-label="Add a comment…"]',
    "comment_post": 'div[role="button"]:has-text("Post")',
    "follow": 'div[role="button"]:has-text("Follow")',
    "unfollow": 'div[role="button"]:has-text("Following")',
    "composer_new_post": 'svg[aria-label="New post"]',
    "upload_input": 'input[type="file"][accept*="image"], input[type="file"][accept*="video"]',
    "share_button": 'div[role="button"]:has-text("Share")',
    "caption_box": 'textarea[aria-label*="caption"]',
    "notifications_heart": 'svg[aria-label="Notifications"]',
    "dm_inbox": 'svg[aria-label="Messenger"]',
    "dm_box": 'div[contenteditable="true"][aria-label*="Message"]',
    "dm_send": 'div[role="button"]:has-text("Send")',
}

QUIRKS = (
    "Checkpoint challenges are common on fresh profiles — expect one. "
    "Reels vs feed posts share the like/comment icons but live under "
    "different routes (/reel/ vs /p/). Story viewers and DMs are separate "
    "surfaces; recipes target feed posts. Instagram aggressively rate-limits "
    "new accounts: keep browser action volumes low for the first weeks."
)


def _s(name):
    return SELECTORS[name]


def like(target_url):
    return [("goto", {"url": target_url}), ("click", {"selector": _s("like")})]


def comment(target_url, text):
    return [("goto", {"url": target_url}),
            ("click", {"selector": _s("comment_toggle")}),
            ("fill", {"selector": _s("comment_box"), "text": text}),
            ("click", {"selector": _s("comment_post")})]


def follow(profile_url):
    return [("goto", {"url": profile_url}), ("click", {"selector": _s("follow")})]


def unfollow(profile_url):
    return [("goto", {"url": profile_url}),
            ("click", {"selector": _s("unfollow")})]


def post_photo(photo_path, caption=""):
    steps = [("goto", {"url": HOME_URL}),
             ("click", {"selector": _s("composer_new_post")}),
             ("upload", {"selector": _s("upload_input"), "file": photo_path}),
             ("click", {"selector": _s("share_button")})]
    if caption:
        steps.insert(-1, ("fill", {"selector": _s("caption_box"),
                                   "text": caption}))
    return steps


def dm_send(thread_url, text):
    return [("goto", {"url": thread_url}),
            ("fill", {"selector": _s("dm_box"), "text": text}),
            ("click", {"selector": _s("dm_send")})]


def hide_comment(target_url):
    return [("goto", {"url": target_url})]


ACTIONS = {"like": like, "comment": comment, "follow": follow,
           "unfollow": unfollow, "post_photo": post_photo,
           "dm_send": dm_send, "hide_comment": hide_comment}
