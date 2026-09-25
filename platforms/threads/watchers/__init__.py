""" Threads watchers: the watcher types Threads registers with the
shared Watcher Engine.

Watcher CLASSES live exactly once in ``core.watcher_engine.watchers``;
this module is pure data — membership + platform defaults. The engine
owns scheduling, lifecycle, event dispatch and crash recovery.

Threads vocabulary notes: the shared ``comment`` watcher covers replies
to a thread; ``feed`` covers posts, reposts and quotes in the timeline.
There is no retweet concept — Threads has reposts and quotes instead.
"""

import sys

PLATFORM = "threads"

# NOTE (2026-09-25): no 'message' watcher is registered here. DMs are
# owned EXCLUSIVELY by dm_agents/, so the watcher and the DM agent can
# never double-handle a conversation.
WATCHERS = [
    ('notification', {}),
    ('comment', {'post_id': 'latest'}),
    ('feed', {}),
    ('follow', {'targets': []}),
    ('activity', {}),
    ('trend', {}),
    ('mention', {}),
    ('crisis', {}),
    ('security', {}),
]

# watcher type -> offline fixture filename (under core/watcher_engine/fixtures/)
FIXTURE_FILES = {
    'notification': 'notifications.json',
    'comment': 'comments.json',
    'feed': 'feed.json',
    'follow': 'follow_targets.json',
    'activity': 'activity.json',
    'trend': 'trend.json',
    'mention': 'mention.json',
    'crisis': 'crisis.json',
}


def register(engine, account="", fixtures_dir=None):
    """Register every Threads watcher with the shared engine."""
    return engine.register_platform_package(sys.modules[__name__],
                                            account=account,
                                            fixtures_dir=fixtures_dir)
