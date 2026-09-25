"""Missions + autonomy CLI tests (subprocess, isolated state)."""

import json
import os

import pytest

from conftest import add_account, cli, state, write_policy


def make_mission(home, name="m1"):
    mdir = os.path.join(home, "missions")
    os.makedirs(mdir, exist_ok=True)
    r = cli("mission", "create", "--name", name,
            "--platforms", "tiktok", "--topics", "ai video,sora",
            "--actions", "post,like,follow",
            "--limit", "posts_per_day=2", "--limit", "likes_per_day=5",
            home=home, missions=mdir)
    assert r.returncode == 0, r.stderr
    return name


def _mc(home, *args):
    return cli(*args, home=home,
               missions=os.path.join(home, "missions"))


def test_mission_create_list_show(home):
    mdir = os.path.join(home, "missions")
    os.makedirs(mdir, exist_ok=True)
    make_mission(home)
    r = _mc(home, "mission", "list")
    assert r.returncode == 0 and "m1" in r.stdout
    r = _mc(home, "mission", "show", "m1")
    assert r.returncode == 0 and "tiktok" in r.stdout and "ai video" in r.stdout
    # duplicate create fails
    r = _mc(home, "mission", "create", "--name", "m1", "--platforms", "tiktok",
            "--actions", "like")
    assert r.returncode == 1
    # dm can never be mission-scoped
    r = _mc(home, "mission", "create", "--name", "bad", "--platforms", "tiktok",
            "--actions", "dm")
    assert r.returncode == 1


def test_autonomy_grant_requires_confirm(home):
    make_mission(home)
    r = _mc(home, "autonomy", "grant", "--mission", "m1")
    assert r.returncode == 1 and "--confirm" in r.stderr + r.stdout
    r = _mc(home, "autonomy", "status")
    assert "not granted" in r.stdout


def test_autonomy_grant_revoke_status(home):
    make_mission(home)
    r = _mc(home, "autonomy", "grant", "--mission", "m1", "--confirm")
    assert r.returncode == 0 and "GRANTED" in r.stdout
    r = _mc(home, "autonomy", "status")
    assert "GRANTED" in r.stdout and "m1" in r.stdout
    assert _mc(home, "autonomy", "revoke").returncode == 0
    r = _mc(home, "autonomy", "status")
    assert "not granted" in r.stdout


def test_autonomous_like_in_scope_auto_approves(home):
    add_account(home)
    make_mission(home)
    _mc(home, "autonomy", "grant", "--mission", "m1", "--confirm")
    r = _mc(home, "engage", "like", "--platform", "tiktok", "--account", "main",
            "--target", "v1", "--author", "creator_x",
            "--text", "sora ai video tutorial", "--likes-count", "500")
    assert r.returncode == 0, r.stderr
    assert "AUTO-APPROVED" in r.stdout
    a = state(home, "actions.json")[0]
    assert a["status"] == "approved" and a["auto_approved"] is True
    assert a["mission"] == "m1"


def test_autonomous_out_of_scope_blocked(home):
    add_account(home)
    add_account(home, platform="instagram", username="ig_user", label="main")
    make_mission(home)
    _mc(home, "autonomy", "grant", "--mission", "m1", "--confirm")
    # wrong platform
    r = _mc(home, "engage", "like", "--platform", "instagram", "--account", "main",
            "--target", "v9")
    assert r.returncode == 2 and "scope" in r.stderr
    # comment action not in mission's allowed actions -> blocked
    r = _mc(home, "engage", "comment", "--platform", "tiktok", "--account", "main",
            "--target", "v9", "--text", "hello")
    assert r.returncode == 2 and "scope" in r.stderr
    # refusals logged
    with open(os.path.join(home, "refusals.jsonl")) as fh:
        lines = fh.read().strip().split("\n")
    assert len(lines) == 2


def test_autonomy_off_means_manual_approval(home):
    add_account(home)
    make_mission(home)  # mission exists but autonomy NOT granted
    r = _mc(home, "engage", "like", "--platform", "tiktok", "--account", "main",
            "--target", "v1")
    assert r.returncode == 0 and "DRY-RUN proposal" in r.stdout
    assert state(home, "actions.json")[0]["status"] == "proposed"


def test_mission_limit_accepts_both_limit_key_styles(home, tmp_path, monkeypatch):
    """Regression: check_mission_limit must enforce caps whether the mission
    stores them as posts_per_day or max_posts_per_day (agent-growth uses the
    max_ form; the old key_map silently skipped both)."""
    import autonomy as autonomy_mod
    import missions as missions_mod
    mdir = str(tmp_path / "missions")
    monkeypatch.setenv("SOCIAL_AGENT_MISSIONS", mdir)
    missions_mod.create_mission(
        "captest", ["x"], ["automation"],
        ["post", "like", "reply"],
        {"max_posts_per_day": 1, "likes_per_day": 2,
         "max_replies_per_day": 1})
    autonomy_mod.grant("captest")
    # max_ form enforced: second post raises
    autonomy_mod.check_mission_limit("post")
    try:
        autonomy_mod.check_mission_limit("post")
    except RuntimeError as e:
        assert "1/1" in str(e)
    else:
        raise AssertionError("post cap not enforced")
    # plain form enforced too
    autonomy_mod.check_mission_limit("like")
    autonomy_mod.check_mission_limit("like")
    try:
        autonomy_mod.check_mission_limit("like")
    except RuntimeError as e:
        assert "2/2" in str(e)
    else:
        raise AssertionError("like cap not enforced")
    # reply (previously unmapped) enforced via max_ form
    autonomy_mod.check_mission_limit("reply")
    try:
        autonomy_mod.check_mission_limit("reply")
    except RuntimeError:
        pass
    else:
        raise AssertionError("reply cap not enforced")
