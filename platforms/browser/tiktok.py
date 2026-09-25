"""TikTok browser recipe (no API) — extends the existing login story.

The repo already signs into TikTok through a headed browser session
(first login ~2026-09-24, persistent profile). This recipe adds the
action selectors so TikTok joins the other five platforms on the same
browser backend.
"""

LAST_VERIFIED = "2026-09-25"
HOME_URL = "https://www.tiktok.com/"

LOGIN_NOTES = (
    "Login via QR code, email, or Google — the human picks in the headed "
    "window. TikTok shows email-verification challenges on new devices; "
    "the user completed this manually on 2026-09-24. Persistent profile "
    "keeps the session."
)

SELECTORS = {
    "like": '[data-e2e="like-icon"]',
    "comment_toggle": '[data-e2e="comment-icon"]',
    "comment_box": '[data-e2e="comment-input"]',
    "comment_post": '[data-e2e="comment-post"]',
    "follow": '[data-e2e="follow-button"]',
    "unfollow": '[data-e2e="follow-button"]',
    "upload_entry": '[data-e2e="nav-upload"]',
    "upload_input": 'input[type="file"][accept*="video"]',
    "upload_caption": '[data-e2e="caption"]',
    "upload_post": '[data-e2e="post-button"]',
    "notifications_bell": '[data-e2e="nav-inbox"]',
    "dm_thread": '[data-e2e="chat-list-item"]',
    "dm_box": '[data-e2e="chat-input"]',
    "dm_send": '[data-e2e="chat-send"]',
}

QUIRKS = (
    "data-e2e attributes are TikTok's stable surface — prefer them over "
    "classes. Uploads go through the web upload page with a caption field "
    "and Post button; processing takes a while — wait_for the Post button "
    "to enable. Comments on some videos are disabled; the recipe fails "
    "cleanly (wait_for timeout) and the journal records it."
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


def post_video(video_path, caption=""):
    steps = [("goto", {"url": "https://www.tiktok.com/upload"}),
             ("upload", {"selector": _s("upload_input"), "file": video_path}),
             ("wait_for", {"selector": _s("upload_post")})]
    if caption:
        steps.append(("fill", {"selector": _s("upload_caption"),
                                "text": caption}))
    steps.append(("click", {"selector": _s("upload_post")}))
    return steps


def dm_send(thread_url, text):
    return [("goto", {"url": thread_url}),
            ("fill", {"selector": _s("dm_box"), "text": text}),
            ("click", {"selector": _s("dm_send")})]


ACTIONS = {"like": like, "comment": comment, "follow": follow,
           "unfollow": unfollow, "post_video": post_video,
           "dm_send": dm_send}
