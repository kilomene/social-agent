"""Watcher framework unit tests: schemas, detection, idempotency, proposals."""

import json
import os

import pytest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.watcher_engine import REGISTRY, WatcherError, FIXTURES_DIR
from core.watcher_engine.framework import Watcher

FX = FIXTURES_DIR


def make(wtype, home, config=None, fixture=None):
    cls = REGISTRY[wtype]
    return cls("testw", "tiktok", "tester", config or {}, home, fixture)


def test_all_fifteen_types_registered():
    assert sorted(REGISTRY) == ["activity", "channel", "comment", "competitor",
                                "content-idea", "crisis", "feed", "follow",
                                "mention", "message", "notification",
                                "security", "sentiment", "trend", "velocity"]


def test_config_validation(tmp_path):
    w = make("comment", str(tmp_path))  # missing required post_id
    assert any("post_id" in e for e in w.validate_config())
    w2 = make("comment", str(tmp_path), {"post_id": "v1", "bogus": 1})
    assert any("bogus" in e for e in w2.validate_config())
    w3 = make("comment", str(tmp_path), {"post_id": "v1"})
    assert w3.validate_config() == []


def test_notification_detect_and_propose(tmp_path):
    w = make("notification", str(tmp_path),
             fixture=os.path.join(FX, "notifications.json"))
    events = w.check()
    assert len(events) == 4
    mentions = [e for e in events if e["kind"] == "notification:mention"]
    assert mentions[0]["proposed_action"]["action"] == "reply"
    assert mentions[0]["severity"] == "high"
    likes = [e for e in events if e["kind"] == "notification:like"]
    assert likes[0]["proposed_action"] is None
    # idempotent second run
    assert w.check() == []


def test_comment_watcher_flagging(tmp_path):
    w = make("comment", str(tmp_path),
             {"post_id": "vid123", "flag_keywords": ["giveaway"]},
             os.path.join(FX, "comments.json"))
    events = w.check()
    assert len(events) == 3
    flagged = [e for e in events if e["severity"] == "high"]
    assert len(flagged) == 1 and "giveaway" in flagged[0]["summary"]


def test_feed_keyword_filtering(tmp_path):
    w = make("feed", str(tmp_path), {"keywords": ["sora"]},
             os.path.join(FX, "feed.json"))
    events = w.check()
    assert len(events) == 1
    assert "sora" in events[0]["data"]["matched_keywords"]


def test_follow_watcher_targets(tmp_path):
    w = make("follow", str(tmp_path),
             {"targets": [{"kind": "user", "value": "dagreat00100"}]},
             os.path.join(FX, "follow_targets.json"))
    events = w.check()
    assert len(events) == 1
    assert events[0]["data"]["watched"] == {"kind": "user", "value": "dagreat00100"}


def test_activity_watcher_delta(tmp_path):
    import shutil
    fx = os.path.join(str(tmp_path), "activity.json")
    shutil.copy(os.path.join(FX, "activity.json"), fx)
    w = make("activity", str(tmp_path), fixture=fx)
    # first poll: baseline recorded silently (nothing to diff against)
    assert w.check() == []
    # new snapshot arrives -> delta events
    with open(fx, encoding="utf-8") as fh:
        data = json.load(fh)
    data["items"].append({"id": "s3", "followers": 1650, "posts": 43,
                          "timestamp": "2026-09-25T00:00:00Z"})
    with open(fx, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    events = w.check()
    kinds = {e["kind"] for e in events}
    assert "activity:followers" in kinds and "activity:posts" not in kinds
    f = next(e for e in events if e["kind"] == "activity:followers")
    assert f["data"] == {"metric": "followers", "old": 1641, "new": 1650, "delta": 9}
    # same snapshot again -> no new events
    assert w.check() == []


def test_channel_and_message_watchers(tmp_path):
    w = make("channel", str(tmp_path), {"channel": "UC123"},
             os.path.join(FX, "channel.json"))
    events = w.check()
    assert len(events) == 1 and events[0]["kind"] == "channel:upload"
    m = make("message", str(tmp_path), fixture=os.path.join(FX, "messages.json"))
    mevents = m.check()
    assert len(mevents) == 1
    assert mevents[0]["proposed_action"]["action"] == "dm"
    assert mevents[0]["severity"] == "high"


def test_events_appended_to_log(tmp_path):
    home = str(tmp_path)
    w = make("notification", home, fixture=os.path.join(FX, "notifications.json"))
    w.check()
    log = os.path.join(home, "events.jsonl")
    assert os.path.exists(log)
    with open(log, encoding="utf-8") as fh:
        lines = [json.loads(l) for l in fh if l.strip()]
    assert len(lines) == 4
    assert all(l["watcher"] == "testw" for l in lines)


def test_check_raises_on_bad_config(tmp_path):
    w = make("comment", str(tmp_path))  # missing post_id
    with pytest.raises(WatcherError):
        w.check()


def test_base_watcher_never_acts(tmp_path):
    """The framework exposes no acting methods at all."""
    assert not hasattr(Watcher, "post")
    assert not hasattr(Watcher, "like")
    assert not hasattr(Watcher, "comment")
    assert not hasattr(Watcher, "follow")
