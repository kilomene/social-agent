"""Tests: growth module (playbooks, goals, audit, youtube packaging)."""

import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from growth import strategy, goals, audit, youtube
from conftest import add_account, cli, state


def test_playbook_all_platforms_have_entries():
    for p in strategy.list_platforms():
        pb = strategy.playbook(p)
        assert pb, p
        assert isinstance(pb, dict), p


def test_playbook_unknown_platform_raises():
    try:
        strategy.playbook("myspace")
    except (KeyError, ValueError):
        return
    raise AssertionError("expected KeyError/ValueError for unknown platform")


def test_goals_roundtrip_and_progress(tmp_path):
    home = str(tmp_path / "h")
    g = goals.set_goal(home, "youtube", "main", 10000, "2026-12-31",
                       label="10k", starting_followers=500)
    assert g["target_followers"] == 10000
    assert len(goals.load_goals(home)) == 1
    prog = goals.progress(home, g, followers=3000)
    assert prog["current"] == 3000
    assert prog["percent"] > 0
    milestones = goals.check_milestones(home, g, prog)
    assert isinstance(milestones, list)


def test_audit_scores_all_pillars():
    res = audit.audit("youtube", "main", {
        "posts_per_week": 3, "avg_views": 4200, "followers": 850,
        "avg_likes": 180, "avg_comments": 12, "niche": "AI video tutorials",
        "has_bio": True, "has_link": False, "has_avatar": True, "has_cta": True,
    })
    assert set(res["pillars"]) == {"consistency", "hooks", "niche_clarity",
                                   "engagement_rate", "profile_conversion"}
    assert all("score" in s and "detail" in s for s in res["pillars"].values())
    assert res["fixes"], "audit must suggest fixes"
    # unknown metrics are never guessed
    res2 = audit.audit("youtube", "main", {})
    assert res2["overall"] is None


def test_youtube_titles_five_scored_sorted():
    vs = youtube.title_variants("my cat pays rent", "cat")
    assert len(vs) == 5
    assert all({"title", "formula", "score"} <= set(v) for v in vs)
    scores = [v["score"] for v in vs]
    assert scores == sorted(scores, reverse=True)


def test_youtube_preflight_required_gate():
    ok, missing = youtube.preflight({})
    assert not ok and "title" in " ".join(missing).lower()
    ok, _ = youtube.preflight({item["key"]: True for item in youtube.QUALITY_CHECKLIST})
    assert ok


def test_youtube_description_and_thumbnail_brief():
    d = youtube.build_description("My title", summary="hello",
                                  timestamps=["0:00 intro"],
                                  links=[("Gear", "https://x.com")],
                                  hashtags=["ai"])
    assert "My title" in d and "https://x.com" in d and "#ai" in d
    b = youtube.thumbnail_brief("cat pays rent")
    assert "cat pays rent" in b


def test_cli_growth_playbook_and_audit(home):
    r = cli("growth", "playbook", "--platform", "tiktok", home=home)
    assert r.returncode == 0, r.stderr
    r = cli("growth", "goals", "set", "--platform", "tiktok", "--account", "main",
            "--target-followers", "5000", "--deadline", "2026-12-31", home=home)
    assert r.returncode == 0, r.stderr
    r = cli("growth", "goals", "list", home=home)
    assert r.returncode == 0 and "5000" in r.stdout, r.stderr
    r = cli("growth", "audit", "--platform", "tiktok", "--account", "main",
            "--followers", "100", "--posts-per-week", "2", home=home)
    assert r.returncode == 0 and "consistency" in r.stdout, r.stderr


def test_cli_youtube_titles_and_preflight(home):
    r = cli("youtube", "titles", "my idea", home=home)
    assert r.returncode == 0, r.stderr
    assert len([l for l in r.stdout.splitlines() if l.startswith("[")]) == 5
    r = cli("youtube", "preflight", "--audio", home=home)
    assert r.returncode == 2  # missing required fields -> refused
    assert "thumbnail" in r.stderr.lower()
