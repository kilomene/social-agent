"""Engagement intelligence: interest scoring and anti-spam guards.

Used by `engage like`, the feed watcher, and the follow watcher to decide
what is worth engaging with — and to refuse engagement that looks like spam.
Pure stdlib.
"""

from .interest import load_profile, score_post, score_user, extract_hashtags

__all__ = ["load_profile", "score_post", "score_user", "extract_hashtags"]
