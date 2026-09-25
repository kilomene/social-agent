"""Threads as a full platform: adapter, ToS, watchers, workspace, DM stub.

No-API like everything else: approved actions become execution tickets
(hands/) fulfilled by the host agent in its own live browser.
"""

import os

import yaml

from platforms.base import get_adapter, SUPPORTED_PLATFORMS
from platforms import tos as tos_mod

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_threads_is_a_supported_platform():
    assert "threads" in SUPPORTED_PLATFORMS
    a = get_adapter("threads")
    assert a.name == "threads"
    d = a.to_dict()
    assert d["display"] == "Threads"
    assert d["readable"] and d["postable"]
    # honest ToS gap is declared in the adapter itself
    assert any("unauthorized automation" in s for s in d["not_possible"])


def test_threads_tos_rules():
    path = os.path.join(REPO, "platforms", "threads", "tos_rules.yaml")
    rules = yaml.safe_load(open(path))
    assert rules["platform"] == "threads"
    assert str(rules["last_checked"]) == "2026-09-25"
    acts = rules["actions"]
    # when in doubt, restricted: automation is not affirmatively permitted
    for action in ("automated_likes", "automated_comments",
                   "automated_follows", "automated_reshares",
                   "automated_dms", "automated_posting",
                   "automated_data_collection", "automated_reading",
                   "profile_modification"):
        assert acts[action]["status"] == "restricted", action
        assert acts[action]["basis"] and acts[action]["sources"], action
    assert acts["comment_moderation"]["status"] == "allowed"
    assert os.path.isfile(os.path.join(REPO, "platforms", "threads",
                                       "terms.md"))


def test_threads_tos_restricted_not_refused():
    rule = tos_mod.check_tos("threads", "automated_likes")
    assert rule["status"] == "restricted"


def test_threads_watchers_register_with_engine(home):
    from core.watcher_engine import WatcherEngine
    import platforms.threads.watchers as tw
    assert tw.PLATFORM == "threads"
    assert len(tw.WATCHERS) == 9
    e = WatcherEngine(home)
    recs = tw.register(e, account="main")
    assert len(recs) == 9
    assert {r["platform"] for r in recs} == {"threads"}
    assert {r["id"] for r in recs} == {f"threads:{t}" for t, _ in tw.WATCHERS}
    # DMs are owned EXCLUSIVELY by dm_agents: no message watcher
    assert "threads:message" not in {r["id"] for r in recs}
    # memory view is namespaced to threads
    import platforms.threads.memory as tmem
    v = tmem.view(home)
    assert v.platform == "threads"


def test_threads_platform_tree_complete():
    base = os.path.join(REPO, "platforms", "threads")
    for sub in ("watchers", "memory", "workspace"):
        assert os.path.isdir(os.path.join(base, sub)), sub
    # no persistent-profile leftovers anywhere in the platform tree
    assert not os.path.exists(os.path.join(base, "browser_profile"))
    assert os.path.isfile(os.path.join(base, "workspace", "workspace.yaml"))


def test_threads_dm_adapter_is_stub():
    from dm_agents import get_adapter as dm_get_adapter
    from dm_agents.platforms import SUPPORTED as DM_SUPPORTED
    assert "threads" in DM_SUPPORTED
    mod = dm_get_adapter("threads")
    assert mod.PLATFORM == "threads"
    assert mod.STATUS == "stub"
    ok, reason = mod.readiness()
    assert ok is False
    assert "no account registered" in reason
    assert "no verified web DM flow" in reason
