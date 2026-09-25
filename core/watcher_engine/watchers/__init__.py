"""Watcher implementations: ONE copy of each watcher class, shared by every
platform. Platforms do not copy these — they REGISTER the ones they need
with the Watcher Engine (core.watcher_engine.engine)."""

from .activity_watcher import ActivityWatcher
from .channel_watcher import ChannelWatcher
from .comment_watcher import CommentWatcher
from .content_idea_watcher import ContentIdeaWatcher
from .competitor_watcher import CompetitorWatcher
from .crisis_watcher import CrisisWatcher
from .feed_watcher import FeedWatcher
from .follow_watcher import FollowWatcher
from ..framework import Watcher, WatcherError
from .mention_watcher import MentionWatcher
from .message_watcher import MessageWatcher
from .notification_watcher import NotificationWatcher
from .security_watcher import SecurityWatcher
from .sentiment_watcher import SentimentWatcher
from .trend_watcher import TrendWatcher
from .velocity_watcher import VelocityWatcher

REGISTRY = {
    cls.type: cls
    for cls in (
        NotificationWatcher,
        CommentWatcher,
        FeedWatcher,
        FollowWatcher,
        ActivityWatcher,
        ChannelWatcher,
        MessageWatcher,
        TrendWatcher,
        CompetitorWatcher,
        SentimentWatcher,
        MentionWatcher,
        VelocityWatcher,
        ContentIdeaWatcher,
        CrisisWatcher,
        SecurityWatcher,
    )
}

__all__ = ["REGISTRY", "Watcher", "WatcherError"]
