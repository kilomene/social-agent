"""Persistent browser sessions: one profile dir per account.

``<home>/accounts/<label>/browser-profile/`` holds the Chromium profile:
cookies, localStorage, logins — everything survives agent restarts,
exactly like a person's own browser. A small ``browser.json`` sidecar
records session state (never credentials).

First-time login is a HEADED session the user drives themselves
(`browser login <account>`): the agent opens the platform's login page,
the human signs in (handling 2FA themselves), then closes the window.
After that the agent reuses the persistent profile headlessly.

2FA/challenge: the agent NEVER tries to bypass a challenge. It pauses,
notifies the user via the notification channel, and waits.
"""

import json
import os
from datetime import datetime, timezone

from browser.driver import PlaywrightDriver, SimulatedDriver

ACCOUNTS_DIR = "accounts"
PROFILE_DIR = "browser-profile"
SIDECAR = "browser.json"

# login URLs per platform (first-login landing pages)
LOGIN_URLS = {
    "facebook": "https://www.facebook.com/login",
    "instagram": "https://www.instagram.com/accounts/login/",
    "x": "https://x.com/i/flow/login",
    "youtube": "https://accounts.google.com/signin",
    "reddit": "https://www.reddit.com/login",
    "tiktok": "https://www.tiktok.com/login",
}

# text markers that suggest a challenge/2FA wall is showing
CHALLENGE_MARKERS = (
    "verify it's you", "two-factor", "2-step verification",
    "enter the code", "check your phone", "unusual login",
    "checkpoint", "suspicious login attempt",
)


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def account_dir(home, label):
    return os.path.join(home, ACCOUNTS_DIR, label)


def profile_dir(home, label):
    """Profile dir for an account.

    When the account is linked to an identity, this resolves to that
    identity's ONE shared browser profile (all platforms, one human
    browser). Otherwise it falls back to the legacy per-account dir.
    """
    legacy = os.path.join(account_dir(home, label), PROFILE_DIR)
    try:
        from identity import store as _ids
        return _ids.resolve_profile_dir(home, label, legacy_dir=legacy)
    except Exception:  # noqa: BLE001 - identity store is optional
        return legacy


def sidecar_path(home, label):
    return os.path.join(account_dir(home, label), SIDECAR)


def load_session(home, label):
    p = sidecar_path(home, label)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def save_session(home, label, info):
    os.makedirs(account_dir(home, label), exist_ok=True)
    p = sidecar_path(home, label)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=2)
    os.replace(tmp, p)
    return info


def init_profile(home, label, platform):
    """Create the persistent profile dir + sidecar (idempotent)."""
    pdir = profile_dir(home, label)
    os.makedirs(pdir, exist_ok=True)
    info = load_session(home, label) or {}
    info.update({"label": label, "platform": platform,
                 "profile_dir": pdir, "status": info.get("status", "new"),
                 "created_at": info.get("created_at", utcnow()),
                 "updated_at": utcnow()})
    saved = save_session(home, label, info)
    # register in permanent memory so the resume engine can cross-check
    # the registry against the on-disk profile after a crash
    try:
        from core import memory as _mem
        from identity import store as _ids
        iid = _ids.identity_for_account(home, label) or ""
        _mem.session_register(home, label, pdir, platform, identity_id=iid)
    except Exception:  # noqa: BLE001 - memory registry is best-effort here
        pass
    return saved


def detect_challenge(page_text):
    """Heuristic: does the page look like a 2FA/challenge wall?"""
    low = (page_text or "").lower()
    return any(m in low for m in CHALLENGE_MARKERS)


def mark_challenge(home, label, kind="2fa"):
    """Record a challenge; the agent pauses and notifies the user."""
    from listen import notify  # local import: listen is a top-level module
    info = load_session(home, label) or {"label": label}
    info.update({"status": "challenge", "challenge": kind,
                 "challenged_at": utcnow(), "updated_at": utcnow()})
    save_session(home, label, info)
    notify(home,
           f"Browser session for account '{label}' hit a {kind} challenge."
           " The agent has PAUSED — it will not try to bypass it."
           f" Please complete the verification in a headed session"
           f" (`browser login {label}`), then the agent can resume.",
           kind="browser_challenge")
    return info


def clear_challenge(home, label):
    info = load_session(home, label) or {"label": label}
    info.update({"status": "active",
                 "challenge": None, "updated_at": utcnow()})
    return save_session(home, label, info)


def open_login_session(home, label, platform, headed=True,
                       driver=None, simulate=False):
    """Open a (headed) session on the platform's login page for the human.

    Returns {"driver": driver, "info": sidecar}. The human completes the
    sign-in in the visible window; the persistent profile keeps the login.
    """
    if platform not in LOGIN_URLS:
        raise ValueError(f"unknown platform {platform!r}")
    info = init_profile(home, label, platform)
    drv = driver or (SimulatedDriver() if simulate else PlaywrightDriver())
    drv.start(profile_dir(home, label), headed=headed)
    try:
        drv.goto(LOGIN_URLS[platform])
    except Exception:
        drv.stop()
        raise
    info.update({"status": "login_pending", "updated_at": utcnow()})
    save_session(home, label, info)
    return {"driver": drv, "info": info,
            "instructions": (
                f"A {'headed' if headed else 'headless'} browser is now open"
                f" at the {platform} login page for account '{label}'.\n"
                "Sign in yourself (handle any 2FA in the window), then close"
                " the browser. Your login persists in"
                f" {profile_dir(home, label)} and the agent will reuse it.\n"
                "The agent never sees or stores your password.")}


def open_reuse_session(home, label, headed=False, driver=None,
                       simulate=False):
    """Reopen the persistent profile for agent-driven work.

    Refuses when no profile exists (login first) or a challenge is open.
    """
    info = load_session(home, label)
    if info is None or not os.path.isdir(profile_dir(home, label)):
        raise RuntimeError(
            f"no browser profile for '{label}' — run `browser login {label}`"
            " first (headed, you sign in).")
    if info.get("status") == "challenge":
        raise RuntimeError(
            f"account '{label}' has an open {info.get('challenge')}"
            " challenge — resolve it with `browser login"
            f" {label}` before the agent resumes.")
    drv = driver or (SimulatedDriver() if simulate else PlaywrightDriver())
    drv.start(profile_dir(home, label), headed=headed)
    return {"driver": drv, "info": info}
