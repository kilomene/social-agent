"""Watcher registry: type name -> watcher class."""

from .activity_watcher import ActivityWatcher
from .channel_watcher import ChannelWatcher
from .comment_watcher import CommentWatcher
from .feed_watcher import FeedWatcher
from .follow_watcher import FollowWatcher
from .framework import Watcher, WatcherError
from .message_watcher import MessageWatcher
from .notification_watcher import NotificationWatcher

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
    )
}

__all__ = ["REGISTRY", "Watcher", "WatcherError"]
