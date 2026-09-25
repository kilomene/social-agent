"""People memory tests: scoring, top fans, notes/tags, CLI."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from people import db
from conftest import add_account, cli, state


def test_upsert_and_score_weights(tmp_path):
    home = str(tmp_path / "home")
    db.upsert(home, "tester", "fan1", "like")
    db.upsert(home, "tester", "fan1", "comment", text="great video!")
    db.upsert(home, "tester", "fan1", "dm", text="hello")
    rec = db.get(home, "tester", "fan1")
    assert rec["counts"]["like"] == 1
    assert rec["counts"]["comment"] == 1
    assert rec["counts"]["dm"] == 1
    # like=1 + comment=3 + dm=5 = 9
    assert db.score(rec) == 9
    assert rec["last_text"] == "hello"


def test_top_ordering(tmp_path):
    home = str(tmp_path / "home")
    for _ in range(2):
        db.upsert(home, "tester", "quiet", "like")
    db.upsert(home, "tester", "loud", "follow")
    ranked = db.top(home, "tester", n=5)
    assert ranked[0][0] == "loud"      # follow=4 > 2 likes=2
    assert ranked[1][0] == "quiet"


def test_qualifies_as_top_fan(tmp_path):
    home = str(tmp_path / "home")
    for _ in range(4):
        db.upsert(home, "tester", "newbie", "comment", text="hi")
    assert not db.qualifies_as_top_fan(home, "tester", "newbie")
    db.upsert(home, "tester", "newbie", "comment", text="again")
    assert db.qualifies_as_top_fan(home, "tester", "newbie")
    db.add_tag(home, "tester", "newbie", "top-fan")
    assert db.is_top_fan(home, "tester", "newbie")


def test_notes_and_tags(tmp_path):
    home = str(tmp_path / "home")
    db.upsert(home, "tester", "pal", "follow")
    db.add_note(home, "tester", "pal", "met at the sora meetup")
    db.add_tag(home, "tester", "pal", "collaborator")
    db.add_tag(home, "tester", "pal", "collaborator")  # idempotent
    rec = db.get(home, "tester", "pal")
    assert rec["notes"] and rec["notes"][0]["text"] == "met at the sora meetup"
    assert rec["tags"] == ["collaborator"]
    db.remove_tag(home, "tester", "pal", "collaborator")
    assert db.get(home, "tester", "pal")["tags"] == []


def test_people_cli(home):
    add_account(home)
    r = cli("people", "note", "--account", "main", "fan1",
            "asked about the tutorial", home=home)
    assert r.returncode == 0, r.stderr
    r = cli("people", "tag", "--account", "main", "fan1", "top-fan", home=home)
    assert r.returncode == 0, r.stderr
    r = cli("people", "show", "--account", "main", "fan1", home=home)
    assert r.returncode == 0 and "tutorial" in r.stdout
    r = cli("people", "untag", "--account", "main", "fan1", "top-fan",
            home=home)
    assert r.returncode == 0, r.stderr
    r = cli("people", "top", "--account", "main", home=home)
    assert r.returncode == 0 and "fan1" in r.stdout


def test_people_cli_unknown_handle(home):
    add_account(home)
    r = cli("people", "show", "--account", "main", "ghost", home=home)
    assert r.returncode != 0
