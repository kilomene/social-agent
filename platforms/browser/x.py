"""X (Twitter) browser recipe (no API).

IMPORTANT — ToS: X's terms require API-only automation; browser-driven
likes/comments/follows/DMs are classified PROHIBITED by the repo's ToS
layer (platforms/x/tos_rules.yaml) and fail closed by default. The user
may explicitly opt in via policy.yaml `tos.acknowledged_risk: [x]`, which
downgrades the prohibition to restricted WITH a loud logged advisory.
Without that acknowledgment this recipe refuses to run. See
platforms/x/terms.md.
"""

LAST_VERIFIED = "2026-09-25"
HOME_URL = "https://x.com/home"

LOGIN_NOTES = (
    "Multi-step flow: username → password, sometimes an extra "
    "'verify username/phone' step. X shows login walls to logged-out "
    "visitors aggressively — the persistent profile avoids them once the "
    "human signs in. 'Unusual login' challenges go to the human."
)

SELECTORS = {
    "like": '[data-testid="like"]',
    "comment_toggle": '[data-testid="reply"]',
    "comment_box": '[data-testid="tweetTextarea_0"]',
    "comment_post": '[data-testid="tweetButton"]',
    "follow": '[data-testid$="-follow"]',
    "unfollow": '[data-testid$="-unfollow"]',
    "composer_toggle": '[data-testid="SideNav_NewTweet_Button"]',
    "composer_box": '[data-testid="tweetTextarea_0"]',
    "composer_post": '[data-testid="tweetButtonInline"]',
    "upload_input": 'input[data-testid="fileInput"]',
    "notifications_bell": '[data-testid="AppTabBar_Notifications_Link"]',
    "dm_inbox": '[data-testid="AppTabBar_DirectMessage_Link"]',
    "dm_box": '[data-testid="dmComposerTextInput"]',
    "dm_send": '[data-testid="dmComposerSendButton"]',
}

QUIRKS = (
    "data-testid attributes are the stable surface on X — they change less "
    "often than classes. Login walls ('login wall' interstitial) appear for "
    "logged-out sessions; a healthy persistent profile avoids them. Tweet "
    "composer and reply composer share testids but live in different dialogs. "
    "X rate-limits viewing aggressively for fresh accounts."
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


ACTIONS = {"like": like, "comment": comment, "follow": follow,
           "unfollow": unfollow, "post_text": post_text,
           "post_video": post_video, "dm_send": dm_send}
