"""browser: persistent browser automation engine (no APIs, no keys).

Everything the agent does on Facebook, Instagram, X, YouTube, Reddit
(and TikTok) goes through a real browser with a persistent profile per
account — logins and cookies survive restarts, exactly like a person's
own browser.

Engine: Playwright (see browser/SETUP.md for install). The Driver
interface keeps all browser code testable: tests use SimulatedDriver,
never a real browser.

Every primitive logs to the audit journal with an idempotency key
(core/recovery.py), so a crashed browser session resumes instead of
repeating a post.
"""

from browser.driver import (BROWSER_OK, Driver, PlaywrightDriver,
                            SimulatedDriver, require_playwright)
from browser import session as session_mod
from browser import human as human_mod
from browser import primitives as primitives_mod

__all__ = ["BROWSER_OK", "Driver", "PlaywrightDriver", "SimulatedDriver",
           "require_playwright", "session_mod", "human_mod",
           "primitives_mod"]
