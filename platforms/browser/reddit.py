"""Reddit browser recipe (no API).

ToS note: Reddit's terms prohibit automated voting (vote manipulation).
The repo's ToS layer classifies upvote/downvote as PROHIBITED and fail
closed — this recipe therefore offers NO vote actions, only comment,
follow (user follow), post, and DM (chat) actions that stay within the
rules. Do not add voting to this recipe.
"""

LAST_VERIFIED = "2026-09-25"
HOME_URL = "https://www.reddit.com/"

LOGIN_NOTES = (
    "Username + password on reddit.com/login. Occasional 'verify you're "
    "human' interstitials — the human clears them in the headed window."
)

SELECTORS = {
    "comment_toggle": 'button:has-text("Reply")',
    "comment_box": 'div[contenteditable="true"]',
    "comment_submit": 'button:has-text("Comment")',
    "user_follow": 'button:has-text("Follow")',
    "user_unfollow": 'button:has-text("Unfollow")',
    "create_post": 'a[href*="/submit"]',
    "post_title": 'input[name="title"]',
    "post_body": 'div[contenteditable="true"]',
    "post_submit": 'button:has-text("Post")',
    "notifications_bell": 'button[aria-label="Notifications"]',
    "chat_icon": 'button[aria-label="Open chat"]',
    "dm_box": 'div[contenteditable="true"][aria-label*="Message"]',
    "dm_send": 'button[aria-label="Send message"]',
}

QUIRKS = (
    "Old vs new Reddit DOM differ — recipes target the new (shreddit) UI. "
    "NO voting actions: automated upvotes/downvotes are prohibited by "
    "Reddit's terms (vote manipulation). Subreddit rules vary; posting is "
    "proposal-gated by the moderation layer before any browser action."
)


def _s(name):
    return SELECTORS[name]


def comment(target_url, text):
    return [("goto", {"url": target_url}),
            ("click", {"selector": _s("comment_toggle")}),
            ("fill", {"selector": _s("comment_box"), "text": text}),
            ("click", {"selector": _s("comment_submit")})]


def follow_user(profile_url):
    return [("goto", {"url": profile_url}),
            ("click", {"selector": _s("user_follow")})]


def unfollow_user(profile_url):
    return [("goto", {"url": profile_url}),
            ("click", {"selector": _s("user_unfollow")})]


def post_text(submit_url, title, body=""):
    steps = [("goto", {"url": submit_url}),
             ("fill", {"selector": _s("post_title"), "text": title})]
    if body:
        steps.append(("fill", {"selector": _s("post_body"), "text": body}))
    steps.append(("click", {"selector": _s("post_submit")}))
    return steps


def dm_send(thread_url, text):
    return [("goto", {"url": thread_url}),
            ("fill", {"selector": _s("dm_box"), "text": text}),
            ("click", {"selector": _s("dm_send")})]


ACTIONS = {"comment": comment, "follow_user": follow_user,
           "unfollow_user": unfollow_user, "post_text": post_text,
           "dm_send": dm_send}
