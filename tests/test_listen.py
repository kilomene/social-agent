"""Notification listener tests: event routing to queue, people, notifications."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import listen
from approvals import queue as q
from people import db as people_db
from conftest import add_account, cli, state


def _policy():
    return {"approvals": {"per_type": {}},
            "moderation": {"auto_hide": [
                {"label": "spam-keyword", "pattern": "buy followers",
                 "reason": "spam"},
            ]}}


def _ev(kind, data, platform="tiktok", account="tester"):
    return {"watcher_type": kind.split(":")[0], "kind": kind,
            "platform": platform, "account": account, "data": data}


def test_question_comment_queues_reply_draft(tmp_path):
    home = str(tmp_path / "home")
    outs = listen.route_event(home, _policy(), _ev(
        "comment:new", {"id": "c1", "author": "curious",
                        "text": "how do you make the background blur?"}))
    assert any("reply draft" in o for o in outs)
    items = q.list_items(home)
    assert len(items) == 1 and items[0]["type"] == "reply"
    assert items[0]["status"] == "pending"
    assert items[0]["payload"]["draft"]
    # the asker is remembered in the people DB
    assert people_db.get(home, "tester", "curious")["counts"]["comment"] == 1


def test_toxic_comment_proposes_hide(tmp_path):
    home = str(tmp_path / "home")
    outs = listen.route_event(home, _policy(), _ev(
        "comment:new", {"id": "c2", "author": "troll9",
                        "text": "you are an idiot, kill yourself"}))
    assert any("hide proposal" in o for o in outs)
    items = q.list_items(home)
    assert items[0]["type"] in ("hide_spam", "hide_other")
    assert items[0]["ref"]["store"] == "moderation.json"


def test_spam_auto_hide_rule_still_applies(tmp_path):
    home = str(tmp_path / "home")
    outs = listen.route_event(home, _policy(), _ev(
        "comment:new", {"id": "c3", "author": "spammer",
                        "text": "buy followers cheap, crypto double your money"}))
    assert any("hide proposal" in o and "approved" in o for o in outs)
    items = q.list_items(home)
    assert items[0]["status"] == "approved"


def test_dm_logged_and_notified(tmp_path):
    home = str(tmp_path / "home")
    outs = listen.route_event(home, _policy(), _ev(
        "message:new", {"sender": "fan2", "text": "love your work!"}))
    assert any("DM" in o for o in outs)
    rec = people_db.get(home, "tester", "fan2")
    assert rec["counts"]["dm"] == 1
    notes = state(home, "notifications.json")
    assert any(n["kind"] == "dm" for n in notes)


def test_notification_kinds_upsert_people(tmp_path):
    home = str(tmp_path / "home")
    listen.route_event(home, _policy(), _ev(
        "notification:new", {"author": "liker", "text": ""}, ))
    # kind without ':' defaults to a mention upsert
    assert people_db.get(home, "tester", "liker") is not None
    listen.route_event(home, _policy(),
                       {"watcher_type": "notification", "kind": "notification:follow",
                        "platform": "tiktok", "account": "tester",
                        "data": {"author": "newfan"}})
    assert people_db.get(home, "tester", "newfan")["counts"]["follow"] == 1


def test_top_fan_auto_tag_and_priority(tmp_path):
    home = str(tmp_path / "home")
    for i in range(5):
        listen.route_event(home, _policy(), _ev(
            "comment:new", {"id": f"c{i}", "author": "superfan",
                            "text": "another great one, love this series"}))
    assert people_db.is_top_fan(home, "tester", "superfan")
    outs = listen.route_event(home, _policy(), _ev(
        "comment:new", {"id": "c9", "author": "superfan",
                        "text": "what camera do you use?"}))
    assert any("PRIORITY" in o for o in outs)
    items = q.list_items(home)
    reply = next(i for i in items if i["type"] == "reply"
                 and i["payload"].get("priority"))
    assert reply is not None


def test_listen_once_over_fixture_watchers(home, tmp_path):
    add_account(home)
    fix = tmp_path / "comments.json"
    fix.write_text("[]", encoding="utf-8")
    r = cli("watch", "start", "--type", "comment", "--platform", "tiktok",
            "--account", "main", "--set", "post_id=vid9",
            "--fixture", str(fix), "--id", "lw1", home=home)
    assert r.returncode == 0, r.stderr
    r = cli("listen", "once", home=home)
    assert r.returncode == 0, r.stderr
    assert "listen pass complete" in r.stdout
