"""LinkedIn as a full platform: adapter, browser recipe, ToS, watchers,
workspace — browser-only like everything else."""

import os

import pytest
import yaml

from platforms.base import get_adapter, SUPPORTED_PLATFORMS
from platforms.browser import RECIPES, get as get_recipe
from platforms import tos as tos_mod

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_linkedin_is_a_supported_platform():
    assert "linkedin" in SUPPORTED_PLATFORMS
    a = get_adapter("linkedin")
    assert a.name == "linkedin"
    d = a.to_dict()
    assert d["display"] == "LinkedIn"
    assert d["readable"] and d["postable"]
    # honest ToS gap is declared in the adapter itself
    assert any("User Agreement" in s for s in d["not_possible"])


def test_linkedin_browser_recipe():
    assert "linkedin" in RECIPES
    mod = get_recipe("linkedin")
    assert mod.LAST_VERIFIED == "2026-09-25"
    assert mod.HOME_URL.startswith("https://www.linkedin.com")
    assert mod.LOGIN_NOTES and mod.QUIRKS
    assert isinstance(mod.SELECTORS, dict) and mod.SELECTORS
    assert isinstance(mod.ACTIONS, dict) and mod.ACTIONS
    steps = mod.ACTIONS["like"](target_url="https://www.linkedin.com/posts/1")
    assert steps[0][0] == "goto"
    # recipe has no API surface
    src = open(os.path.join(REPO, "platforms", "browser",
                            "linkedin.py")).read().lower()
    assert "api_key" not in src and "api key" not in src


def test_linkedin_tos_rules():
    path = os.path.join(REPO, "platforms", "linkedin", "tos_rules.yaml")
    rules = yaml.safe_load(open(path))
    assert rules["platform"] == "linkedin"
    assert str(rules["last_checked"]) == "2026-09-25"
    acts = rules["actions"]
    for action in ("automated_likes", "automated_comments",
                   "automated_follows", "automated_reshares",
                   "automated_dms", "automated_data_collection"):
        assert acts[action]["status"] == "prohibited", action
    assert acts["automated_posting"]["status"] == "restricted"
    assert acts["comment_moderation"]["status"] == "allowed"
    assert os.path.isfile(os.path.join(REPO, "platforms", "linkedin",
                                       "terms.md"))


def test_linkedin_tos_enforced_fail_closed(home):
    with pytest.raises(tos_mod.ToSRefusal):
        tos_mod.check_tos("linkedin", "automated_data_collection")
    with pytest.raises(tos_mod.ToSRefusal):
        tos_mod.check_tos("linkedin", "automated_likes")


def test_linkedin_watchers_register_with_engine(home):
    from core.watcher_engine import WatcherEngine, REGISTRY
    import platforms.linkedin.watchers as lw
    assert lw.PLATFORM == "linkedin"
    e = WatcherEngine(home)
    recs = lw.register(e, account="main")
    assert len(recs) == len(REGISTRY) - 1  # all but channel
    assert {r["platform"] for r in recs} == {"linkedin"}
    # memory view is namespaced to linkedin
    import platforms.linkedin.memory as lmem
    v = lmem.view(home)
    assert v.platform == "linkedin"
    # browser_profile is a pointer, not data
    import json as _json
    ptr = _json.load(open(os.path.join(
        REPO, "platforms", "linkedin", "browser_profile", "profile.json")))
    assert ptr["pointer"] is True


def test_linkedin_platform_tree_complete():
    base = os.path.join(REPO, "platforms", "linkedin")
    for sub in ("watchers", "memory", "browser_profile", "workspace"):
        assert os.path.isdir(os.path.join(base, sub)), sub
    assert os.path.isfile(os.path.join(base, "workspace", "workspace.yaml"))
