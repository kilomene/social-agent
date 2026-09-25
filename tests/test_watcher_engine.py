"""Watcher Engine: registration, lifecycle, checkpoints, crash recovery.

The engine owns scheduling, lifecycle, event dispatch and crash recovery.
Platforms register their watchers (data-only manifests); watcher classes
live exactly once in core.watcher_engine.watchers.
"""

import json
import os

import pytest

from core.watcher_engine import (DuplicateWatcherError, REGISTRY,
                                 WatcherEngine, WatcherError, FIXTURES_DIR)
from core.watcher_engine.engine import UnknownWatcherTypeError
from core import event_bus
from core import memory as mem


def _engine(home):
    return WatcherEngine(home)


def test_register_and_duplicate_refused(home):
    e = _engine(home)
    rec = e.register("w1", "notification", "tiktok", "main",
                     fixture=os.path.join(FIXTURES_DIR, "notifications.json"))
    assert rec["id"] == "w1"
    assert rec["enabled"] is True
    with pytest.raises(DuplicateWatcherError):
        e.register("w1", "notification", "tiktok", "main")
    with pytest.raises(UnknownWatcherTypeError):
        e.register("w2", "nope", "tiktok", "main")
    with pytest.raises(WatcherError):
        # comment watcher requires post_id
        e.register("w3", "comment", "tiktok", "main", config={})
    # invalid config refused at registration, not at poll time
    assert e.get("w2") is None


def test_register_platform_manifest(home):
    e = _engine(home)
    import platforms.tiktok.watchers as tw
    recs = tw.register(e, account="main")
    assert len(recs) == len(REGISTRY) - 1  # all but channel
    assert {r["platform"] for r in recs} == {"tiktok"}
    ids = {r["id"] for r in recs}
    assert "tiktok:notification" in ids
    # registering the same platform again is refused per-watcher
    with pytest.raises(DuplicateWatcherError):
        tw.register(e, account="main")
    # youtube gets the channel watcher too
    e2 = WatcherEngine(home + "-2")
    import platforms.youtube.watchers as yw
    recs2 = yw.register(e2, account="main")
    assert len(recs2) == len(REGISTRY)
    assert "youtube:channel" in {r["id"] for r in recs2}


def test_registry_persists_across_engine_instances(home):
    e = _engine(home)
    e.register("w1", "feed", "x", "main")
    e2 = _engine(home)  # "restart"
    assert e2.get("w1")["type"] == "feed"
    e2.disable("w1")
    assert _engine(home).get("w1")["enabled"] is False


def test_poll_writes_checkpoint_to_memory_db(home):
    e = _engine(home)
    e.register("tiktok:notification", "notification", "tiktok", "main",
               fixture=os.path.join(FIXTURES_DIR, "notifications.json"))
    events = e.poll("tiktok:notification")
    assert len(events) == 4
    cp = mem.checkpoint_get(home, "tiktok:notification")
    assert cp is not None
    assert cp["platform"] == "tiktok"
    assert cp["cursor"]["polls"] == 1
    assert len(cp["cursor"]["seen_ids"]) == 4
    # second poll: no duplicates (checkpoint replayed)
    events2 = e.poll("tiktok:notification")
    assert events2 == []
    cp2 = mem.checkpoint_get(home, "tiktok:notification")
    assert cp2["cursor"]["polls"] == 2


def test_kill_mid_poll_resume_no_missed_no_duplicates(home, tmp_path):
    """Simulate a crash between polls: new engine instance replays the
    checkpoint from the shared memory DB — new items found, old ones
    never re-emitted."""
    fx = tmp_path / "notifs.json"
    fx.write_text(json.dumps([
        {"id": "a", "kind": "mention", "author": "x", "text": "hi"},
        {"id": "b", "kind": "like", "author": "y"},
    ]))
    e = _engine(home)
    e.register("tiktok:notification", "notification", "tiktok", "main",
               fixture=str(fx))
    assert len(e.poll("tiktok:notification")) == 2
    # --- VM dies here. New engine, same home (same memory.db) ---
    fx.write_text(json.dumps([
        {"id": "a", "kind": "mention", "author": "x", "text": "hi"},
        {"id": "b", "kind": "like", "author": "y"},
        {"id": "c", "kind": "follow", "author": "z"},
    ]))
    e2 = _engine(home)
    events = e2.poll("tiktok:notification")
    assert [ev["data"]["id"] for ev in events] == ["c"]  # only the new one
    report = e2.resume_report(platform="tiktok")
    assert report[0]["seen"] == 3
    assert report[0]["has_checkpoint"] is True


def test_poll_disabled_watcher_refused(home):
    e = _engine(home)
    e.register("w1", "feed", "x", "main")
    e.disable("w1")
    with pytest.raises(WatcherError):
        e.poll("w1")


def test_tos_check_injected_and_enforced(home):
    calls = []

    def _tos(platform):
        calls.append(platform)
        raise WatcherError("ToS says no")

    e = WatcherEngine(home, tos_check=_tos)
    e.register("w1", "feed", "x", "main")
    with pytest.raises(WatcherError):
        e.poll("w1")
    assert calls == ["x"]


def test_event_bus_dispatch(home):
    event_bus.clear()
    seen = []
    event_bus.subscribe("notification:", lambda h, ev: seen.append(ev["id"]))
    e = _engine(home)
    e.register("tiktok:notification", "notification", "tiktok", "main",
               fixture=os.path.join(FIXTURES_DIR, "notifications.json"))
    e.poll("tiktok:notification")
    assert len(seen) == 4  # dispatched by kind prefix
    # persisted to the event log too
    logged = event_bus.read_events(home)
    assert len(logged) == 4
    event_bus.clear()


def test_engine_lists_by_platform(home):
    e = _engine(home)
    import platforms.tiktok.watchers as tw
    import platforms.x.watchers as xw
    tw.register(e, account="a")
    xw.register(e, account="b")
    assert len(e.watchers_for_platform("tiktok")) == len(REGISTRY) - 1
    assert len(e.list(enabled_only=True)) == 2 * (len(REGISTRY) - 1)
    res = e.poll_all()
    assert set(res) == {"tiktok", "x"}
    assert "tiktok:notification" in res["tiktok"]
