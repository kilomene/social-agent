"""Identity store: multiple persistent social identities per installation.

Layout under ``<home>/identity/``::

    accounts/          per social account: handle, platform, persona file,
                       owner name            (<label>.json)
    browser_profiles/  registry mapping accounts -> ONE shared persistent
                       browser profile dir per identity (<id>.json)
    permissions/       per-identity grants (<id>.json)
    fingerprints/      per-identity browser fingerprint notes (<id>.json)
    identities.db      SQLite registry tying it all together

Key rule: every identity shares ONE browser profile across ALL platforms
(one logged-in human browser, many tabs — exactly like a real user).
Platform workspaces never get their own profiles.

Permissions are FAIL-CLOSED: no grant = no action. `may()` returns False
for unknown identities, unknown actions, or missing grants.

Fingerprints are human-consistency notes (the user's real UA/viewport/
locale/timezone so automation matches their actual browser). This is
NOT spoofing/rotation tooling — there is no fingerprint randomization
here, by design.
"""

import json
import os
import re
import sqlite3
from datetime import datetime, timezone

DB_NAME = os.path.join("identity", "identities.db")

ACCOUNTS_DIR = os.path.join("identity", "accounts")
PROFILES_DIR = os.path.join("identity", "browser_profiles")
PERMS_DIR = os.path.join("identity", "permissions")
FINGERPRINTS_DIR = os.path.join("identity", "fingerprints")

SCHEMA = """
CREATE TABLE IF NOT EXISTS identities (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, owner_name TEXT DEFAULT '',
    created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS identity_accounts (
    identity_id TEXT NOT NULL, account_label TEXT NOT NULL,
    platform TEXT NOT NULL, handle TEXT DEFAULT '',
    PRIMARY KEY (identity_id, account_label));
CREATE TABLE IF NOT EXISTS permissions (
    identity_id TEXT PRIMARY KEY, grants_json TEXT DEFAULT '{}',
    updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS fingerprints (
    identity_id TEXT PRIMARY KEY, user_agent TEXT DEFAULT '',
    viewport TEXT DEFAULT '', locale TEXT DEFAULT '',
    timezone TEXT DEFAULT '', notes TEXT DEFAULT '',
    updated_at TEXT NOT NULL);
"""


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(name):
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    if not slug:
        raise ValueError("identity name is required")
    return slug


def _connect(home):
    os.makedirs(os.path.join(home, "identity"), exist_ok=True)
    cx = sqlite3.connect(os.path.join(home, DB_NAME))
    cx.row_factory = sqlite3.Row
    cx.executescript(SCHEMA)
    return cx


def _write_json(home, subdir, name, data):
    d = os.path.join(home, subdir)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name + ".json")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, p)
    return p


def _read_json(home, subdir, name):
    p = os.path.join(home, subdir, name + ".json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------ identities ---

def create_identity(home, name, owner_name=""):
    """Create a new persistent identity. Returns the identity record."""
    iid = _slug(name)
    cx = _connect(home)
    try:
        cx.execute(
            "INSERT INTO identities (id, name, owner_name, created_at)"
            " VALUES (?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET owner_name=excluded.owner_name",
            (iid, name, owner_name, utcnow()))
        cx.commit()
        row = cx.execute("SELECT * FROM identities WHERE id = ?",
                         (iid,)).fetchone()
    finally:
        cx.close()
    _write_json(home, ACCOUNTS_DIR, f"identity-{iid}",
                {"identity_id": iid, "name": name,
                 "owner_name": owner_name, "accounts": []})
    _write_json(home, PERMS_DIR, iid,
                {"identity_id": iid, "grants": {}, "updated_at": utcnow()})
    _write_json(home, FINGERPRINTS_DIR, iid,
                {"identity_id": iid, "user_agent": "", "viewport": "",
                 "locale": "", "timezone": "", "notes": ""})
    _init_shared_profile(home, iid)
    return dict(row)


def get_identity(home, identity_id):
    cx = _connect(home)
    try:
        row = cx.execute("SELECT * FROM identities WHERE id = ?",
                         (identity_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["accounts"] = [dict(r) for r in cx.execute(
            "SELECT account_label, platform, handle FROM identity_accounts"
            " WHERE identity_id = ? ORDER BY account_label", (identity_id,))]
        return d
    finally:
        cx.close()


def list_identities(home):
    cx = _connect(home)
    try:
        return [dict(r) for r in cx.execute(
            "SELECT * FROM identities ORDER BY id").fetchall()]
    finally:
        cx.close()


def link_account(home, identity_id, account_label, platform, handle=""):
    """Attach a social account to an identity (shares its browser profile)."""
    if get_identity(home, identity_id) is None:
        raise KeyError(f"unknown identity {identity_id!r}")
    cx = _connect(home)
    try:
        cx.execute(
            "INSERT INTO identity_accounts (identity_id, account_label,"
            " platform, handle) VALUES (?, ?, ?, ?)"
            " ON CONFLICT(identity_id, account_label) DO UPDATE SET"
            " platform=excluded.platform, handle=excluded.handle",
            (identity_id, account_label, platform, handle))
        cx.commit()
    finally:
        cx.close()
    _write_json(home, ACCOUNTS_DIR, account_label,
                {"identity_id": identity_id, "label": account_label,
                 "platform": platform, "handle": handle,
                 "owner_name": get_identity(home, identity_id).get(
                     "owner_name", "")})
    _profile_registry_add(home, identity_id, account_label, platform)
    return get_identity(home, identity_id)


def unlink_account(home, identity_id, account_label):
    cx = _connect(home)
    try:
        cx.execute(
            "DELETE FROM identity_accounts WHERE identity_id = ?"
            " AND account_label = ?", (identity_id, account_label))
        cx.commit()
    finally:
        cx.close()
    try:
        os.remove(os.path.join(home, ACCOUNTS_DIR, account_label + ".json"))
    except OSError:
        pass


def identity_for_account(home, account_label):
    """Which identity owns this account label? (None if unlinked)."""
    cx = _connect(home)
    try:
        row = cx.execute(
            "SELECT identity_id FROM identity_accounts"
            " WHERE account_label = ? LIMIT 1", (account_label,)).fetchone()
        return row["identity_id"] if row else None
    finally:
        cx.close()


# ------------------------------------------------------- browser profiles ---

def _init_shared_profile(home, identity_id):
    """One shared profile dir per identity (all platforms, one browser)."""
    profile_dir = os.path.join(home, PROFILES_DIR, identity_id, "profile")
    os.makedirs(profile_dir, exist_ok=True)
    data = _read_json(home, PROFILES_DIR, identity_id) or {}
    data.update({"identity_id": identity_id, "profile_dir": profile_dir,
                 "accounts": data.get("accounts", []),
                 "updated_at": utcnow(),
                 "note": "ONE shared browser profile for every platform"
                         " used by this identity (one human browser)."})
    _write_json_here = os.path.join(home, PROFILES_DIR, identity_id + ".json")
    tmp = _write_json_here + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, _write_json_here)
    return profile_dir


def _profile_registry_add(home, identity_id, account_label, platform):
    data = _read_json(home, PROFILES_DIR, identity_id) or {}
    accts = data.get("accounts", [])
    entry = {"label": account_label, "platform": platform}
    if entry not in accts:
        accts.append(entry)
    data["accounts"] = accts
    data["updated_at"] = utcnow()
    if "profile_dir" not in data:
        data["profile_dir"] = os.path.join(
            home, PROFILES_DIR, identity_id, "profile")
        os.makedirs(data["profile_dir"], exist_ok=True)
    p = os.path.join(home, PROFILES_DIR, identity_id + ".json")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, p)
    return data


def shared_profile_dir(home, identity_id):
    """The single browser profile dir shared by all of an identity's
    platforms. Created on demand (idempotent)."""
    if get_identity(home, identity_id) is None:
        raise KeyError(f"unknown identity {identity_id!r}")
    return _init_shared_profile(home, identity_id)


def resolve_profile_dir(home, account_label, legacy_dir=None):
    """Profile dir for an account: the identity's SHARED profile when the
    account is linked to an identity, else the legacy per-account dir.

    This is what browser/session.py consults — one human browser per
    identity, many platform tabs."""
    iid = identity_for_account(home, account_label)
    if iid:
        data = _read_json(home, PROFILES_DIR, iid) or {}
        pdir = data.get("profile_dir") or os.path.join(
            home, PROFILES_DIR, iid, "profile")
        os.makedirs(pdir, exist_ok=True)
        return pdir
    return legacy_dir


# ------------------------------------------------------------ permissions ---

def _grants(home, identity_id):
    cx = _connect(home)
    try:
        row = cx.execute(
            "SELECT grants_json FROM permissions WHERE identity_id = ?",
            (identity_id,)).fetchone()
        return json.loads(row["grants_json"]) if row else {}
    finally:
        cx.close()


def set_permissions(home, identity_id, grants):
    """Replace the grant set for an identity (dict)."""
    if get_identity(home, identity_id) is None:
        raise KeyError(f"unknown identity {identity_id!r}")
    if not isinstance(grants, dict):
        raise ValueError("grants must be a dict")
    cx = _connect(home)
    try:
        cx.execute(
            "INSERT INTO permissions (identity_id, grants_json, updated_at)"
            " VALUES (?, ?, ?)"
            " ON CONFLICT(identity_id) DO UPDATE SET"
            " grants_json=excluded.grants_json,"
            " updated_at=excluded.updated_at",
            (identity_id, json.dumps(grants), utcnow()))
        cx.commit()
    finally:
        cx.close()
    _write_json(home, PERMS_DIR, identity_id,
                {"identity_id": identity_id, "grants": grants,
                 "updated_at": utcnow()})
    return grants


def grant(home, identity_id, action):
    """Grant one action to an identity."""
    grants = _grants(home, identity_id)
    actions = set(grants.get("actions", []))
    actions.add(action)
    grants["actions"] = sorted(actions)
    return set_permissions(home, identity_id, grants)


def revoke(home, identity_id, action):
    """Revoke one action from an identity."""
    grants = _grants(home, identity_id)
    actions = set(grants.get("actions", []))
    actions.discard(action)
    grants["actions"] = sorted(actions)
    return set_permissions(home, identity_id, grants)


def may(home, identity_id, action):
    """Fail-closed permission check: no grant = no action."""
    if get_identity(home, identity_id) is None:
        return False
    grants = _grants(home, identity_id)
    actions = grants.get("actions", [])
    return bool(action) and (action in actions or "*" in actions)


def approval_required(home, identity_id, action):
    """Does this action need human approval for this identity?

    Default is True (fail-closed): only actions explicitly listed under
    grants.require_approval_exempt skip the queue."""
    grants = _grants(home, identity_id)
    exempt = set(grants.get("require_approval_exempt", []))
    return action not in exempt


def get_permissions(home, identity_id):
    return _grants(home, identity_id)


# ------------------------------------------------------------ fingerprints ---

def set_fingerprint(home, identity_id, user_agent="", viewport="",
                    locale="", timezone_name="", notes=""):
    """Record the identity's real browser fingerprint notes.

    Human-consistency only: these describe the USER's actual browser so
    automation behaves like them. No rotation, no spoofing — by design."""
    if get_identity(home, identity_id) is None:
        raise KeyError(f"unknown identity {identity_id!r}")
    cx = _connect(home)
    try:
        cx.execute(
            "INSERT INTO fingerprints (identity_id, user_agent, viewport,"
            " locale, timezone, notes, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(identity_id) DO UPDATE SET"
            " user_agent=excluded.user_agent, viewport=excluded.viewport,"
            " locale=excluded.locale, timezone=excluded.timezone,"
            " notes=excluded.notes, updated_at=excluded.updated_at",
            (identity_id, user_agent, viewport, locale, timezone_name,
             notes, utcnow()))
        cx.commit()
        row = cx.execute("SELECT * FROM fingerprints WHERE identity_id = ?",
                         (identity_id,)).fetchone()
    finally:
        cx.close()
    _write_json(home, FINGERPRINTS_DIR, identity_id, dict(row))
    return dict(row)


def get_fingerprint(home, identity_id):
    cx = _connect(home)
    try:
        row = cx.execute("SELECT * FROM fingerprints WHERE identity_id = ?",
                         (identity_id,)).fetchone()
        return dict(row) if row else None
    finally:
        cx.close()


# ------------------------------------------------- platform profile pointers ---

def _repo_platforms_dir():
    """The shipped platforms/ tree (templates + pointers)."""
    return os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "platforms")


def write_platform_profile_pointer(home, platform, identity_id):
    """Record which identity a platform workspace operates as.

    Written to the runtime home (``<home>/workspaces/<platform>/``); the
    shipped ``platforms/<platform>/browser_profile/profile.json`` is the
    template. Resolution always lands on the identity's ONE shared
    persistent profile — no per-platform profile data is ever created.
    """
    get_identity(home, identity_id)  # KeyError if unknown: fail closed
    wdir = os.path.join(home, "workspaces", platform)
    os.makedirs(wdir, exist_ok=True)
    data = {
        "pointer": True,
        "platform": platform,
        "identity_id": identity_id,
        "profile_dir": shared_profile_dir(home, identity_id),
        "note": "POINTER ONLY — resolves to the identity's one shared "
                "persistent browser profile.",
    }
    path = os.path.join(wdir, "browser_profile.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, path)
    return data


def read_platform_profile_pointer(home, platform):
    """Resolve a platform's browser profile to the shared identity profile.

    Returns the absolute profile dir, or None if the platform workspace
    has no identity assigned yet. Never creates profile data.
    """
    runtime = os.path.join(home, "workspaces", platform,
                           "browser_profile.json")
    identity_id = ""
    if os.path.exists(runtime):
        try:
            identity_id = json.load(open(runtime)).get("identity_id", "")
        except (ValueError, OSError):
            identity_id = ""
    if not identity_id:
        # fall back to the shipped template pointer
        template = os.path.join(_repo_platforms_dir(), platform,
                                "browser_profile", "profile.json")
        if os.path.exists(template):
            try:
                identity_id = json.load(open(template)).get(
                    "identity_id", "")
            except (ValueError, OSError):
                identity_id = ""
    if not identity_id:
        return None
    try:
        return shared_profile_dir(home, identity_id)
    except KeyError:
        return None
