"""Facebook browser recipe (no API)."""

LAST_VERIFIED = "2026-09-25"
HOME_URL = "https://www.facebook.com/"

LOGIN_NOTES = (
    "Standard email/phone + password form. May show 'unusual login' "
    "checkpoint on new IPs — the human completes it in the headed window. "
    "Checkpoint: 'Is this you?' device confirmation."
)

SELECTORS = {
    # feed interactions (aria-labels are the stable surface on facebook.com)
    "like": '[aria-label="Like"]',
    "comment_toggle": '[aria-label="Leave a comment"]',
    "comment_box": '[aria-label="Write a comment"] [contenteditable="true"]',
    "follow": '[aria-label="Follow"]',
    "unfollow": '[aria-label="Following"]',
    # composer
    "composer_toggle": '[aria-label="Create a post"]',
    "composer_box": '[aria-label*="What\'s on your mind"] [contenteditable="true"]',
    "composer_post": '[aria-label="Post"]',
    # photo/video upload (composer file input)
    "upload_input": 'input[type="file"][accept*="video"], input[type="file"][accept*="image"]',
    # notifications + messenger
    "notifications_bell": '[aria-label="Notifications"]',
    "messenger_icon": '[aria-label="Messenger"]',
    "dm_thread": '[role="main"] [aria-label*="Conversation"]',
    "dm_box": '[aria-label*="Message"] [contenteditable="true"]',
    "dm_send": '[aria-label="Send"]',
}

QUIRKS = (
    "Infinite scroll feed — scroll the target post into view before acting. "
    "Comment boxes are nested contenteditables; click the toggle first. "
    "Video upload opens a separate composer dialog with its own Post button. "
    "Marketplace/group contexts have different DOM — recipes target the main feed."
)


def _s(name):
    return SELECTORS[name]


def like(target_url):
    return [("goto", {"url": target_url}), ("click", {"selector": _s("like")})]


def comment(target_url, text):
    return [("goto", {"url": target_url}),
            ("click", {"selector": _s("comment_toggle")}),
            ("fill", {"selector": _s("comment_box"), "text": text}),
            ("press", {"key": "Enter"})]


def follow(profile_url):
    return [("goto", {"url": profile_url}), ("click", {"selector": _s("follow")})]


def unfollow(profile_url):
    return [("goto", {"url": profile_url}),
            ("click", {"selector": _s("unfollow")})]


def post_text(text):
    return [("goto", {"url": HOME_URL}),
            ("click", {"selector": _s("composer_toggle")}),
            ("fill", {"selector": _s("composer_box"), "text": text}),
            ("click", {"selector": _s("composer_post")})]


def post_video(video_path, caption=""):
    steps = [("goto", {"url": HOME_URL}),
             ("click", {"selector": _s("composer_toggle")}),
             ("upload", {"selector": _s("upload_input"), "file": video_path}),
             ("wait_for", {"selector": _s("composer_box")})]
    if caption:
        steps.append(("fill", {"selector": _s("composer_box"), "text": caption}))
    steps.append(("click", {"selector": _s("composer_post")}))
    return steps


def dm_send(thread_url, text):
    return [("goto", {"url": thread_url}),
            ("fill", {"selector": _s("dm_box"), "text": text}),
            ("click", {"selector": _s("dm_send")})]


def hide_comment(target_url):
    # own posts only (enforced by the moderation layer, not the recipe)
    return [("goto", {"url": target_url})]


ACTIONS = {"like": like, "comment": comment, "follow": follow,
           "unfollow": unfollow, "post_text": post_text,
           "post_video": post_video, "dm_send": dm_send,
           "hide_comment": hide_comment}
