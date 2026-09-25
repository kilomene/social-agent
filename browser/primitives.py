"""Browser primitives with journaling.

Every primitive (goto, click, fill, scroll, upload, screenshot,
get_text, wait_for) is wrapped so that:

1. the intent is journaled BEFORE execution (core/recovery.py) with an
   idempotency key — a crashed session resumes, never repeats a post;
2. the action passes through the central rate-limit controller;
3. human pacing (randomized delays) and active-hours are honored.

Usage: primitives.do(home, driver, account_label, platform, action,
                    payload, policy, simulate=False)
"""

from browser import human as human_mod
from core import recovery as rec_mod


def _check_rate_limit(home, platform, action, policy):
    from ratelimit import controller as rl
    verdict = rl.check(home, platform, action, policy)
    if not verdict.get("allowed"):
        raise RuntimeError(
            f"rate limit exhausted for {platform}/{action}: retry at"
            f" {verdict.get('retry_at', '?')} — action refused, not dropped")
    rl.consume(home, platform, action)


def do(home, driver, account_label, platform, action, payload=None,
       policy=None, simulate=False, rng=None):
    """Run one browser primitive, journaled + rate-limited + human-paced.

    Returns the primitive's result dict.
    """
    policy = policy or {}
    payload = payload or {}
    # 1. active hours
    if not human_mod.within_active_hours(policy):
        raise RuntimeError("outside configured browser active hours — paused")
    # 2. rate limit (browser actions are NOT exempt)
    _check_rate_limit(home, platform, f"browser_{action}", policy)
    # 3. journal the intent BEFORE executing (idempotency)
    jb = rec_mod.begin(home, f"browser_{action}",
                       payload.get("target") or payload.get("url") or action,
                       {"platform": platform, "account": account_label,
                        "action": action,
                        "payload": {k: v for k, v in payload.items()
                                    if k != "text"}})
    if jb["duplicate"]:
        return {"ok": True, "duplicate": True,
                "note": "already completed — not repeated"}
    try:
        if not simulate:
            human_mod.human_delay(rng=rng)
        result = _dispatch(driver, action, payload)
        # screenshot evidence for acting primitives
        if action in ("click", "fill", "upload", "press") and \
                payload.get("evidence_dir"):
            import os
            ev = os.path.join(payload["evidence_dir"],
                              f"{jb['id']}.png")
            try:
                driver.screenshot(ev)
                result["evidence"] = ev
            except Exception:
                pass
        rec_mod.end(home, jb["id"], True,
                    result=str(result)[:500])
        return result
    except Exception as e:
        rec_mod.end(home, jb["id"], False, error=str(e)[:500])
        # 2FA/challenge mid-session: pause + notify, never bypass
        try:
            text = driver.get_text().get("text", "")
        except Exception:
            text = ""
        from browser.session import detect_challenge, mark_challenge
        if detect_challenge(text):
            mark_challenge(home, account_label, kind="challenge")
        raise


def _dispatch(driver, action, payload):
    if action == "goto":
        return driver.goto(payload["url"])
    if action == "click":
        sel = payload["selector"]
        if payload.get("human", True):
            from browser.human import scroll_before_click
            return scroll_before_click(driver, sel)
        return driver.click(sel)
    if action == "fill":
        return driver.fill(payload["selector"], payload.get("text", ""))
    if action == "press":
        return driver.press(payload.get("key", "Enter"))
    if action == "scroll":
        return driver.scroll(selector=payload.get("selector"),
                             direction=payload.get("direction", "down"),
                             amount=payload.get("amount", 600))
    if action == "upload":
        return driver.upload(payload["selector"], payload["file"])
    if action == "screenshot":
        return driver.screenshot(payload["path"])
    if action == "get_text":
        return driver.get_text(payload.get("selector"))
    if action == "wait_for":
        return driver.wait_for(payload["selector"],
                               payload.get("timeout_ms", 15000))
    raise ValueError(f"unknown browser primitive {action!r}")
