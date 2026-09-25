"""Tests for the persistent browser engine (mocked drivers only)."""

import json
import os

import pytest

from browser import driver as drv_mod
from browser import session as sess_mod
from browser import human as human_mod
from browser import primitives as prim_mod
from platforms import tos as tos_mod
from platforms.browser import get as get_recipe, RECIPES
from platforms.browser import backend as backend_mod


def _policy(**over):
    p = {"rate_limits": {"default": {"actions_per_hour": 1000,
                                     "actions_per_day": 10000}},
         "browser": {"active_hours": {"enabled": False}},
         "platforms": {"x": {"backend": "browser"}},
         "tos": {"acknowledged_risk": []}}
    p.update(over)
    return p


def test_simulated_driver_records(home):
    d = drv_mod.SimulatedDriver()
    d.start(os.path.join(home, "prof"))
    d.goto("https://x.com/home")
    d.click('[data-testid="like"]')
    d.fill("textarea", "hello")
    ops = [a["op"] for a in d.actions]
    assert ops == ["start", "goto", "click", "fill"]
    d.stop()
    assert d.actions[-1]["op"] == "stop"


def test_require_playwright_errors_helpfully():
    if drv_mod.BROWSER_OK:
        pytest.skip("playwright installed here; nothing to assert")
    with pytest.raises(drv_mod.BrowserUnavailable) as ei:
        drv_mod.require_playwright()
    assert "browser/SETUP.md" in str(ei.value)


def test_session_profile_and_login(home):
    info = sess_mod.init_profile(home, "main", "x")
    assert os.path.isdir(sess_mod.profile_dir(home, "main"))
    assert info["platform"] == "x"
    res = sess_mod.open_login_session(home, "main", "x", simulate=True)
    assert "Sign in yourself" in res["instructions"]
    res["driver"].stop()
    info = sess_mod.load_session(home, "main")
    assert info["status"] == "login_pending"


def test_challenge_pauses_and_notifies(home):
    sess_mod.init_profile(home, "main", "x")
    sess_mod.mark_challenge(home, "main", kind="2fa")
    info = sess_mod.load_session(home, "main")
    assert info["status"] == "challenge"
    with pytest.raises(RuntimeError):
        sess_mod.open_reuse_session(home, "main", simulate=True)
    notes = json.load(open(os.path.join(home, "notifications.json")))
    assert any(n["kind"] == "browser_challenge" for n in notes)
    assert sess_mod.detect_challenge("Please verify it's you — enter the code")
    assert not sess_mod.detect_challenge("welcome to your timeline")


def test_human_active_hours():
    assert human_mod.within_active_hours({}) is True
    pol = {"browser": {"active_hours": {"enabled": True, "start": "08:00",
                                        "end": "23:00"}}}
    from datetime import datetime, timezone, timedelta
    noon = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
    night = datetime(2026, 9, 25, 3, 0, tzinfo=timezone.utc)
    assert human_mod.within_active_hours(pol, now=noon) is True
    assert human_mod.within_active_hours(pol, now=night) is False


def test_primitive_journals_and_rate_limits(home):
    pol = _policy()
    d = drv_mod.SimulatedDriver()
    d.start(os.path.join(home, "prof"))
    r = prim_mod.do(home, d, "main", "x", "goto",
                    {"url": "https://x.com/home"}, policy=pol, simulate=True)
    assert r["ok"] is True
    # journal has a completed entry
    entries = [json.loads(l) for l in
               open(os.path.join(home, "audit", "journal.jsonl"))]
    assert any(e["action_type"] == "browser_goto" and
               e["status"] == "completed" for e in entries)
    # rate-limit bucket consumed
    from ratelimit import controller as rl
    st = rl.status(home, pol)
    assert any(b["bucket"] == "x:browser_goto" for b in st)
    # identical primitive again -> idempotent duplicate, not repeated
    r2 = prim_mod.do(home, d, "main", "x", "goto",
                     {"url": "https://x.com/home"}, policy=pol, simulate=True)
    assert r2.get("duplicate") is True
    d.stop()


def test_primitive_rate_limit_refusal(home):
    pol = {"rate_limits": {"default": {"actions_per_hour": 1,
                                       "actions_per_day": 1}},
           "browser": {"active_hours": {"enabled": False}}}
    d = drv_mod.SimulatedDriver()
    d.start(os.path.join(home, "prof"))
    prim_mod.do(home, d, "main", "x", "goto", {"url": "https://x.com/a"},
                policy=pol, simulate=True)
    with pytest.raises(RuntimeError) as ei:
        prim_mod.do(home, d, "main", "x", "goto", {"url": "https://x.com/b"},
                    policy=pol, simulate=True)
    assert "rate limit exhausted" in str(ei.value)
    d.stop()


def test_recipes_have_maintenance_surface():
    assert set(RECIPES) == {"facebook", "instagram", "x", "youtube",
                            "reddit", "tiktok"}
    for name, mod in RECIPES.items():
        assert mod.LAST_VERIFIED, name
        assert isinstance(mod.SELECTORS, dict) and mod.SELECTORS, name
        assert mod.QUIRKS and mod.LOGIN_NOTES, name
        assert isinstance(mod.ACTIONS, dict) and mod.ACTIONS, name
    # spot-check step shapes
    steps = RECIPES["x"].ACTIONS["like"](
        target_url="https://x.com/s/1")
    assert steps[0] == ("goto", {"url": "https://x.com/s/1"})
    assert steps[1][0] == "click"


def test_tos_fail_closed_without_ack(home):
    pol = _policy()
    with pytest.raises(tos_mod.ToSRefusal):
        tos_mod.check_tos("x", "automated_likes", policy=pol, home=home)
    assert not os.path.exists(
        os.path.join(home, "audit", "tos_acknowledgments.jsonl"))


def test_tos_acknowledged_risk_downgrades_with_advisory(home, capsys):
    pol = _policy(tos={"acknowledged_risk": ["x"]})
    rule = tos_mod.check_tos("x", "automated_likes", policy=pol, home=home)
    assert rule["status"] == "restricted"
    assert rule["acknowledged_risk"] is True
    err = capsys.readouterr().err
    assert "ACKNOWLEDGED-RISK ADVISORY" in err
    assert "suspend or ban" in err
    log = os.path.join(home, "audit", "tos_acknowledgments.jsonl")
    assert os.path.exists(log)
    entry = json.loads(open(log).read().strip())
    assert entry["platform"] == "x"


def test_backend_refuses_x_without_ack(home):
    sess_mod.init_profile(home, "main", "x")
    with pytest.raises(tos_mod.ToSRefusal):
        backend_mod.act(home, "x", "main", "like",
                        params={"target_url": "https://x.com/s/1"},
                        policy=_policy(), simulate=True)


def test_backend_proceeds_with_ack(home):
    sess_mod.init_profile(home, "main", "x")
    pol = _policy(tos={"acknowledged_risk": ["x"]})
    res = backend_mod.act(home, "x", "main", "like",
                          params={"target_url": "https://x.com/s/1"},
                          policy=pol, simulate=True)
    assert res["ok"] is True
    assert len(res["steps"]) == 2  # goto + click
    assert res["tos"]["acknowledged_risk"] is True


def test_backend_non_x_needs_no_ack(home):
    sess_mod.init_profile(home, "main", "tiktok")
    res = backend_mod.act(home, "tiktok", "main", "like",
                          params={"target_url": "https://tiktok.com/v/1"},
                          policy=_policy(), simulate=True)
    assert res["ok"] is True
    assert res["tos"]["status"] in ("allowed", "restricted")


def test_backend_rejects_unknown_action(home):
    sess_mod.init_profile(home, "main", "x")
    with pytest.raises(ValueError):
        backend_mod.act(home, "x", "main", "nuke",
                        policy=_policy(tos={"acknowledged_risk": ["x"]}),
                        simulate=True)
