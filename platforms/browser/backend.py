"""Browser backend: execute platform actions through the persistent browser.

`act(home, platform, account_label, action, params, policy, ...)`:

  The browser is the ONLY backend — there is no API backend, no API
  integrations, no API keys, and no config switch. Every platform is
  driven through the account's persistent browser profile.

  1. enforces the ToS layer FIRST (platforms/tos.py), including the
     `tos.acknowledged_risk` opt-in downgrade with its loud advisory;
  2. opens the account's persistent browser profile
     (`browser/session.py`);
  3. runs the recipe's primitive steps, each journaled with an
     idempotency key, human-paced, and rate-limited
     (`browser/primitives.py`).

Action names: like, comment, follow, unfollow, post_text, post_video,
dm_send, hide_comment, subscribe, upload_video, post_photo, follow_user.
Each maps onto a recipe function in platforms/browser/<platform>.py.
"""

from platforms import tos as tos_mod
from platforms.browser import get as get_recipe
from browser import session as session_mod
from browser import primitives as primitives_mod
from browser.driver import PlaywrightDriver, SimulatedDriver

# browser action -> ToS action class (via the CLI op mapping)
ACTION_TO_TOS_CLASS = {
    "like": "like", "comment": "comment", "follow": "follow",
    "unfollow": "follow", "follow_user": "follow",
    "unfollow_user": "follow", "post_text": "post",
    "post_video": "post", "post_photo": "post", "upload_video": "post",
    "dm_send": "dm", "hide_comment": "hide", "subscribe": "follow",
}


def act(home, platform, account_label, action, params=None, policy=None,
        driver=None, simulate=False, headed=False, evidence=True):
    """Execute one browser-backed platform action. Returns a result dict.

    simulate=True uses the offline SimulatedDriver (tests/exams/dry runs).
    Without simulate, requires Playwright (browser/SETUP.md).
    """
    policy = policy or {}
    params = params or {}
    platform = platform.lower()
    recipe = get_recipe(platform)
    if action not in recipe.ACTIONS:
        raise ValueError(
            f"{platform} recipe has no action {action!r}"
            f" (available: {sorted(recipe.ACTIONS)})")
    # ToS FIRST — fail closed unless the user acknowledged the risk.
    tos_class = tos_mod.CLI_OP_TO_CLASS.get(
        ACTION_TO_TOS_CLASS.get(action, action))
    if tos_class is None:
        raise RuntimeError(f"no ToS classification for browser action"
                           f" {action!r}; refusing by default")
    rule = tos_mod.check_tos(platform, tos_class, policy=policy, home=home)
    # persistent session (refuses when no profile / open challenge)
    sess = session_mod.open_reuse_session(
        home, account_label, headed=headed, driver=driver,
        simulate=simulate)
    drv = sess["driver"]
    steps = recipe.ACTIONS[action](**params)
    results = []
    try:
        for op, payload in steps:
            kw = dict(payload)
            if evidence:
                import os
                kw.setdefault("evidence_dir",
                              os.path.join(home, "audit", "evidence"))
                os.makedirs(kw["evidence_dir"], exist_ok=True)
            r = primitives_mod.do(home, drv, account_label, platform, op,
                                  kw, policy=policy, simulate=simulate)
            results.append({"op": op, "ok": r.get("ok", False)})
            if r.get("duplicate"):
                break
    finally:
        try:
            drv.stop()
        except Exception:
            pass
    return {"ok": all(r["ok"] for r in results), "platform": platform,
            "account": account_label, "action": action,
            "steps": results,
            "tos": {"status": rule.get("status"),
                    "acknowledged_risk": bool(rule.get("acknowledged_risk"))}}


def make_driver(simulate=False):
    return SimulatedDriver() if simulate else PlaywrightDriver()
