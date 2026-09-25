"""Interest-scoring model for selective engagement.

A post is "interesting" when it matches the user's interest profile
(`policy.yaml` -> `interests:`): topic/hashtag/author affinity plus minimum
quality signals. Scoring is additive and explainable: every point comes with
a human-readable reason, which is what gets logged when a like is refused.

Item shape (anything dict-like works; missing fields are treated as zero):
    {"author": "creator_x", "text": "...", "title": "...",
     "hashtags": ["aivideo"], "likes": 120, "comments": 8, "views": 5000,
     "bio": "..."}   # bio is used by score_user()
"""

import os
import re

from policy import yaml_lite

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HASHTAG_RE = re.compile(r"#(\w+)")


def default_policy_path():
    return os.environ.get(
        "SOCIAL_AGENT_POLICY", os.path.join(REPO_ROOT, "policy", "policy.yaml"))


def load_profile(path=None):
    """Load the `interests:` section of policy.yaml (never raises)."""
    try:
        with open(path or default_policy_path(), encoding="utf-8") as fh:
            data = yaml_lite.loads(fh.read())
        prof = data.get("interests") or {}
    except Exception:
        prof = {}
    prof.setdefault("enabled", True)
    prof.setdefault("topics", [])
    prof.setdefault("hashtags", [])
    prof.setdefault("authors", [])
    prof.setdefault("quality_signals", {})
    prof.setdefault("weights", {})
    prof.setdefault("threshold", 5)
    return prof


def extract_hashtags(text):
    return [h.lower() for h in HASHTAG_RE.findall(text or "")]


def _num(item, *keys):
    for k in keys:
        v = item.get(k)
        if isinstance(v, (int, float)):
            return v
    return 0


def score_post(item, profile=None):
    """Return (score, reasons, interesting)."""
    profile = profile or load_profile()
    if not profile.get("enabled", True):
        return 0, ["interest profile disabled"], True
    weights = profile.get("weights") or {}
    w_topic = weights.get("topic", 2)
    w_hashtag = weights.get("hashtag", 3)
    w_author = weights.get("author", 4)
    w_quality = weights.get("quality_signal", 1)

    score, reasons = 0, []
    text = f"{item.get('text', '')} {item.get('title', '')}"
    hay = text.lower()
    tags = {t.lower() for t in (item.get("hashtags") or [])} | set(extract_hashtags(text))

    for topic in profile.get("topics") or []:
        if topic and topic.lower() in hay:
            score += w_topic
            reasons.append(f"topic match: {topic!r} (+{w_topic})")
    for ht in profile.get("hashtags") or []:
        if ht and ht.lower().lstrip("#") in tags:
            score += w_hashtag
            reasons.append(f"hashtag match: #{ht.lstrip('#')} (+{w_hashtag})")
    author = str(item.get("author", "")).lower().lstrip("@")
    if author and author in [a.lower().lstrip("@") for a in (profile.get("authors") or [])]:
        score += w_author
        reasons.append(f"author affinity: @{author} (+{w_author})")

    qs = profile.get("quality_signals") or {}
    likes = _num(item, "likes", "like_count")
    comments = _num(item, "comments", "comment_count")
    views = _num(item, "views", "view_count")
    if qs.get("min_likes") and likes >= qs["min_likes"]:
        score += w_quality
        reasons.append(f"quality: {int(likes)} likes >= {qs['min_likes']} (+{w_quality})")
    if qs.get("min_comments") and comments >= qs["min_comments"]:
        score += w_quality
        reasons.append(f"quality: {int(comments)} comments >= {qs['min_comments']} (+{w_quality})")
    if qs.get("min_views") and views >= qs["min_views"]:
        score += w_quality
        reasons.append(f"quality: {int(views)} views >= {qs['min_views']} (+{w_quality})")

    threshold = profile.get("threshold", 5)
    interesting = score >= threshold
    if not reasons:
        reasons.append("no topic/hashtag/author/quality signal matched")
    return score, reasons, interesting


def score_user(user, profile=None, people_tags=None):
    """Score a user dict (for follow decisions). Returns (score, reasons, interesting).

    people_tags: optional list of people-DB tags for this handle — a
    "top-fan" tag adds +2 (documented boost so top fans clear the threshold).
    """
    profile = profile or load_profile()
    weights = profile.get("weights") or {}
    w_topic = weights.get("topic", 2)
    w_author = weights.get("author", 4)
    score, reasons = 0, []
    handle = str(user.get("username") or user.get("author") or "").lower().lstrip("@")
    if handle and handle in [a.lower().lstrip("@") for a in (profile.get("authors") or [])]:
        score += w_author
        reasons.append(f"author affinity: @{handle} (+{w_author})")
    for tag in people_tags or []:
        if tag == "top-fan":
            score += 2
            reasons.append("people-db: top-fan tag (+2)")
    hay = f"{user.get('bio', '')} {user.get('niche', '')}".lower()
    for topic in profile.get("topics") or []:
        if topic and topic.lower() in hay:
            score += w_topic
            reasons.append(f"bio/niche topic match: {topic!r} (+{w_topic})")
            break
    followers = _num(user, "followers", "follower_count")
    min_f = (profile.get("quality_signals") or {}).get("min_followers")
    if min_f and followers >= min_f:
        score += weights.get("quality_signal", 1)
        reasons.append(f"quality: {int(followers)} followers >= {min_f}")
    threshold = profile.get("threshold", 5)
    if not reasons:
        reasons.append("no affinity or topic signal matched")
    return score, reasons, score >= threshold
