"""Human-like operation: pacing, scroll-before-click, active hours.

The agent must behave like a person, not a script:
- randomized delays between actions (never a fixed cadence),
- scroll the target into view before clicking,
- only act inside configured active hours (policy.yaml browser.active_hours),
- every browser action still goes through the central rate-limit controller
  (ratelimit/controller.py) — browser is a backend, not a bypass.
"""

import random
import time
from datetime import datetime


def active_hours_cfg(policy):
    return (policy.get("browser") or {}).get("active_hours") or {}


def within_active_hours(policy, now=None):
    """True when acting is allowed. Disabled/missing config = always."""
    cfg = active_hours_cfg(policy)
    if not cfg.get("enabled"):
        return True
    now = now or datetime.now().astimezone()
    start = cfg.get("start", "08:00")
    end = cfg.get("end", "23:00")
    cur = now.strftime("%H:%M")
    if start <= end:
        return start <= cur < end
    return cur >= start or cur < end  # overnight window


def human_delay(min_s=0.8, max_s=2.8, rng=None):
    """Randomized pause between actions. rng injectable for tests."""
    rng = rng or random
    time.sleep(rng.uniform(min_s, max_s))


def scroll_before_click(driver, selector, rng=None):
    """Scroll the element into view, pause like a human, then click."""
    driver.scroll(selector=selector, direction="down", amount=300)
    human_delay(0.4, 1.2, rng=rng)
    return driver.click(selector)


def type_like_human(driver, selector, text, rng=None):
    """Fill a field, then pause (humans don't instant-submit)."""
    result = driver.fill(selector, text)
    human_delay(0.5, 1.5, rng=rng)
    return result
