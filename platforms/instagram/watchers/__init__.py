""" Instagram watchers: the watcher types Instagram registers with the
shared Watcher Engine.

Watcher CLASSES live exactly once in ``core.watcher_engine.watchers``;
this module is pure data — membership + platform defaults. The engine
owns scheduling, lifecycle, event dispatch and crash recovery.
"""

import sys

PLATFORM = "instagram"

# NOTE (2026-09-25): the 'message' watcher was retired from this
# platform. DMs are owned EXCLUSIVELY by dm_agents/ now, so the
# watcher and the DM agent can never double-handle a conversation.
# Existing installs: run `social-agent watch stop <platform>:message`.
WATCHERS = [
    ('notification', {}),
    ('comment', {'post_id': 'latest'}),
    ('feed', {}),
    ('follow', {'targets': []}),
    ('activity', {}),
    ('trend', {}),
    ('competitor', {'competitors': []}),
    ('sentiment', {}),
    ('mention', {}),
    ('velocity', {}),
    ('content-idea', {}),
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
    'channel': 'channel.json',
    'trend': 'trend.json',
    'competitor': 'competitor.json',
    'sentiment': 'sentiment.json',
    'mention': 'mention.json',
    'velocity': 'velocity.json',
    'content-idea': 'content_idea.json',
    'crisis': 'crisis.json',
}


def register(engine, account="", fixtures_dir=None):
    """Register every Instagram watcher with the shared engine."""
    return engine.register_platform_package(sys.modules[__name__],
                                            account=account,
                                            fixtures_dir=fixtures_dir)
