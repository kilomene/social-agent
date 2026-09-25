"""Watcher Engine: the shared-core service that owns watcher scheduling,
lifecycle, event dispatch and crash recovery.

Every platform REGISTERS its watchers with this one engine
(see platforms/<name>/watchers/). Watcher *implementations* live in
``core.watcher_engine.watchers`` (exactly one copy of each); events flow
out through ``core.event_bus``; checkpoints land in the shared memory DB
so the Resume Engine can restore every platform's watchers where they
stopped.
"""

import os

from .engine import (DuplicateWatcherError, UnknownWatcherTypeError,
                     WatcherEngine)
from .framework import Watcher, WatcherError, as_list, utcnow
from .watchers import REGISTRY

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "fixtures")

__all__ = [
    "Watcher", "WatcherError", "DuplicateWatcherError",
    "UnknownWatcherTypeError", "WatcherEngine", "REGISTRY",
    "FIXTURES_DIR", "as_list", "utcnow",
]
