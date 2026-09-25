"""Tests for comment moderation (classify + auto-hide + watcher wiring)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from moderation import classify as mod
from core.watcher_engine import FIXTURES_DIR
from core.watcher_engine.watchers.comment_watcher import CommentWatcher

FIXTURE = os.path.join(FIXTURES_DIR, "comments_moderation.json")


def test_toxic_flagged():
    r = mod.classify_comment("You are a complete idiot, kill yourself loser")
    assert r["label"] == "toxic"
    assert r["score"] >= 60


def test_slur_flagged():
    r = mod.classify_comment("people like you are subhuman")
    assert r["label"] == "toxic"


def test_spam_link_and_dm():
    r = mod.classify_comment("DM me on telegram for free crypto giveaway!!")
    assert r["label"] == "spam"
    assert any("URL" in x or "DM" in x or "telegram" in x.lower() for x in r["reasons"])


def test_spam_repetition():
    r = mod.classify_comment("free followers free followers free followers click now")
    assert r["label"] == "spam"


def test_question_detected():
    r = mod.classify_comment("How do you get the camera to move like that?")
    assert r["label"] == "question"


def test_praise_detected():
    r = mod.classify_comment("This is amazing 🔥 best video ever")
    assert r["label"] == "praise"


def test_ok_comment():
    r = mod.classify_comment("nice video, watched the whole thing")
    assert r["label"] == "ok"


def test_toxic_beats_spam_priority():
    r = mod.classify_comment("kill yourself http://evil.example")
    assert r["label"] == "toxic"


def test_auto_hide_rule_match():
    rule = mod.check_auto_hide("send me money, double your money now",
                               [{"pattern": "double your money",
                                 "label": "scam", "reason": "money-doubling"}])
    assert rule and rule["label"] == "scam"


def test_auto_hide_no_match():
    assert mod.check_auto_hide("great video!", ["double your money"]) is None


def test_fixture_classification_coverage():
    with open(FIXTURE, encoding="utf-8") as fh:
        items = json.load(fh)
    labels = {mod.classify_comment(i["text"])["label"] for i in items}
    assert {"toxic", "spam", "question", "praise", "ok"} <= labels


def test_comment_watcher_moderation_kinds(tmp_path):
    home = str(tmp_path)
    w = CommentWatcher("w1", "tiktok", "tester",
                       {"post_id": "v1", "moderate": True,
                        "auto_hide_rules": [{"pattern": "double your money",
                                             "label": "scam",
                                             "reason": "money-doubling scam"}]},
                       home, FIXTURE)
    events = w.check()
    kinds = {e["kind"] for e in events}
    assert "comment:toxic" in kinds
    assert "comment:spam" in kinds
    assert "comment:question" in kinds
    # the double-your-money spam comment gets a hide proposal
    hides = [e for e in events if e.get("proposed_action", {}) and
             e["proposed_action"].get("action") == "hide"]
    assert len(hides) == 1
    assert all(e["severity"] == "high"
               for e in events if e["kind"] in ("comment:toxic", "comment:spam"))
    # classification stored in event data for downstream watchers
    assert all("moderation" in e["data"] for e in events)


def test_comment_watcher_no_moderation_by_default(tmp_path):
    home = str(tmp_path)
    w = CommentWatcher("w2", "tiktok", "tester", {"post_id": "v1"}, home, FIXTURE)
    events = w.check()
    assert all(e["kind"] == "comment:new" for e in events)
