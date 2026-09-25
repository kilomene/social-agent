"""Unit tests for the 7 new watcher types (fixture-driven)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.watcher_engine import REGISTRY

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from core.watcher_engine import FIXTURES_DIR
FX = FIXTURES_DIR


def load(name):
    with open(os.path.join(FX, name), encoding="utf-8") as fh:
        return json.load(fh)["items"]


def make(wtype, config, home="/tmp/sa-test-home"):
    cls = REGISTRY[wtype]
    return cls("t1", "tiktok", "examuser", config, home)


def test_registry_has_15_watchers():
    assert len(REGISTRY) == 15
    for t in ["trend", "competitor", "sentiment", "mention", "velocity",
              "content-idea", "crisis", "security"]:
        assert t in REGISTRY, t


def test_security_watcher_urgent_alerts(tmp_path):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    w = make("security", {"accounts": ["main"], "purge_drop_pct": 5,
                          "unfollow_spike": 50, "window_hours": 24,
                          "alert_cooldown_hours": 6})
    items = [
        {"id": "i1", "account": "main", "kind": "follower_delta",
         "prev_followers": 10000, "followers": 9000, "timestamp": now},
        {"id": "i2", "account": "main", "kind": "unfollow",
         "count": 120, "timestamp": now},
        {"id": "i3", "account": "main", "kind": "session", "known": False,
         "session_id": "s9", "ip": "1.2.3.4", "location": "Unknown",
         "timestamp": now},
    ]
    events = w.detect(items)
    kinds = {e["kind"] for e in events}
    assert {"security:follower_purge", "security:unfollow_spike",
            "security:unknown_session"} <= kinds, kinds
    assert all(e["severity"] == "urgent" for e in events)
    # cooldown: same items produce no repeat alerts
    assert w.detect(items) == []


def test_trend_filters_off_mission(tmp_path):
    from conftest import write_policy
    pol = write_policy(str(tmp_path / "p.yaml"),
                       interests={"topics": ["ai video", "sora", "runway"],
                                  "hashtags": ["aivideo"], "threshold": 2})
    os.environ["SOCIAL_AGENT_POLICY"] = pol
    try:
        w = make("trend", {"min_heat": 60, "use_interest_profile": True})
        events = w.detect(load("trend.json"))
        topics = [e["data"]["topic"] for e in events]
        assert "#dancetrend" not in topics  # off-mission -> filtered
        assert any("aivideo" in t for t in topics)
        assert any("runway" in t for t in topics)
        assert all(e["proposed_action"]["action"] == "post" for e in events)
    finally:
        del os.environ["SOCIAL_AGENT_POLICY"]


def test_trend_without_profile_keeps_all_hot(tmp_path):
    w = make("trend", {"min_heat": 70})
    events = w.detect(load("trend.json"))
    assert {e["data"]["topic"] for e in events} == {"#aivideo", "#dancetrend", "#runway"}


def test_competitor_digest(tmp_path):
    w = make("competitor", {"targets": [], "competitors": ["rival_a"]})
    events = w.detect(load("competitor.json"))
    assert len(events) == 1
    assert events[0]["kind"] == "competitor:digest"
    assert "rival_a" in events[0]["summary"] and "9 posts/7d" in events[0]["summary"]


def test_sentiment_shift_detection(tmp_path):
    w = make("sentiment", {"watched_accounts": ["examuser"], "window_size": 6,
                           "shift_threshold": 0.3})
    events = w.detect(load("sentiment.json"))
    downs = [e for e in events if e["kind"] == "sentiment:shift"]
    assert downs, "expected a downward sentiment shift event"
    assert any(e["severity"] == "warning" for e in downs)


def test_mention_filters_handles(tmp_path):
    w = make("mention", {"accounts": ["examuser"]})
    events = w.detect(load("mention.json"))
    assert len(events) == 2
    assert all(e["kind"] == "mention:tagged" for e in events)


def test_velocity_flags_fast_riser(tmp_path):
    w = make("velocity", {"niche_keywords": ["sora", "veo"],
                          "min_velocity": 1000, "propose_engage": False})
    events = w.detect(load("velocity.json"))
    assert len(events) == 1
    assert events[0]["kind"] == "velocity:viral"
    assert events[0]["severity"] == "alert"
    assert events[0]["data"]["velocity_per_hour"] > 1000


def test_content_idea_aggregates_questions(tmp_path):
    w = make("content-idea", {"min_repeats": 3})
    events = w.detect(load("content_idea.json"))
    assert len(events) == 1
    e = events[0]
    assert e["kind"] == "content-idea:request"
    assert e["data"]["count"] >= 3
    assert "sora camera moves tutorial" in e["data"]["question"].lower()
    assert e["proposed_action"]["action"] == "post"


def test_crisis_fires_urgent_on_spike(tmp_path):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    items = load("crisis.json")
    for it in items:
        it["timestamp"] = now  # keep the spike inside the detection window
    w = make("crisis", {"accounts": ["examuser"], "spike_threshold": 5,
                        "window_hours": 6})
    events = w.detect(items)
    assert len(events) == 1
    assert events[0]["kind"] == "crisis:spike"
    assert events[0]["severity"] == "urgent"
    # second poll with same items: no repeat alert (cooldown + dedupe)
    assert w.detect(items) == []
