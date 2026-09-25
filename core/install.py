"""Installer: create one isolated agent workspace ("its own brain").

Creates (default ``~/SocialAgent/``, override with --home or
$SOCIAL_AGENT_HOME)::

    memory.db            permanent SQLite memory (schema initialized)
    backups/             manifests/ + blobs/ + restore_staging/ +
                         versioned <timestamp>/ snapshots + latest pointer
    audit/               journal.jsonl + runner.pid live here
    projects/            Kdenlive/Shotcut projects + render work dirs
    accounts/            per-account files (personas, notes)
    identity/            accounts/ host_sessions/ permissions/
                         fingerprints/ identities.db
    workspaces/          per-platform workspaces (shared core NOT duplicated)
    cache/               disposable downloads / temp media

Idempotent: re-running against an existing install only tops up missing
pieces. Refuses to touch an existing non-empty directory without --force.

Backup provider setup (--remote-provider): optionally configure the
SECONDARY (remote) backup layer at install time. The default (none) is
fully offline — the primary local backup layer always works.
"""

import json
import os
import sys

# Make `core` importable when install.py is run as a script file.
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
from datetime import datetime, timezone

LAYOUT_DIRS = ("backups/manifests", "backups/blobs",
               "backups/restore_staging", "audit", "projects",
               "accounts", "cache",
               "identity/accounts", "identity/host_sessions",
               "identity/permissions", "identity/fingerprints",
               "workspaces")

VERSION = "0.2.0"

REMOTE_PROVIDERS = ("none", "folder", "github", "gdrive", "onedrive",
                    "dropbox", "s3")


def default_home():
    return os.environ.get("SOCIAL_AGENT_HOME") or os.path.expanduser(
        "~/SocialAgent")


def install(home=None, force=False):
    home = os.path.expanduser(home or default_home())
    created, kept = [], []
    if os.path.exists(home) and os.listdir(home) and not force:
        # Never clobber an existing non-empty install blindly.
        marker = os.path.join(home, ".installed.json")
        if os.path.exists(marker):
            pass  # our own install: top up missing pieces below
        else:
            raise SystemExit(
                f"refusing: {home} exists and is not empty (and is not a"
                " social-agent install). Pass --force to overwrite the"
                " layout, or --home <dir> for a fresh isolated install.")
    for sub in LAYOUT_DIRS:
        d = os.path.join(home, sub)
        if os.path.isdir(d):
            kept.append(sub + "/")
        else:
            os.makedirs(d, exist_ok=True)
            created.append(sub + "/")
    # initialize the permanent memory database
    from core import memory as memory_mod
    db = memory_mod.db_path(home)
    if os.path.exists(db):
        kept.append("memory.db")
    else:
        memory_mod.init_db(home)
        created.append("memory.db")
    marker = os.path.join(home, ".installed.json")
    with open(marker, "w", encoding="utf-8") as fh:
        json.dump({"version": VERSION,
                   "installed_at": datetime.now(timezone.utc).isoformat(
                       timespec="seconds"),
                   "layout": list(LAYOUT_DIRS)}, fh, indent=2)
    return {"home": home, "created": created, "kept": kept}


def setup_remote_backup(home, provider, target=""):
    """Configure the optional SECONDARY (remote) backup layer.

    provider "none" (default) = offline-only; the primary local layer
    always works. Any other provider records the user's EXPLICIT consent
    and generates the local encryption key (keys never leave the machine).
    Remote sync stays refused until consent + encryption are both in place.
    """
    from core import remote as remote_mod
    if provider in (None, "none"):
        remote_mod.setup(home, "none")
        return {"provider": None,
                "note": "offline-only: local versioned backups only"}
    cfg = remote_mod.setup(home, provider, target, by="user@install")
    try:
        remote_mod.ensure_key(home)
        enc = "encryption key generated (local only, 0600)"
    except RuntimeError as e:
        enc = f"WARNING: {e} — sync will refuse until fixed"
    return {"provider": provider, "target": target, "consent": "granted",
            "encryption": enc}


def prompt_remote_provider():
    """Interactive backup-provider setup screen (install time)."""
    print()
    print("== Backup provider setup (SECONDARY layer — optional) ==")
    print("The primary layer (automatic versioned snapshots on this VM)")
    print("always works, no internet needed. The secondary layer syncs")
    print("ENCRYPTED backups to a provider you choose. Nothing syncs")
    print("without your explicit consent, ever.")
    print()
    for i, p in enumerate(REMOTE_PROVIDERS):
        print(f"  [{i}] {p}")
    print()
    try:
        choice = input(
            "Choose a provider [0 = none, offline-only]: ").strip()
    except EOFError:
        choice = ""
    if not choice:
        choice = "0"
    try:
        provider = REMOTE_PROVIDERS[int(choice)]
    except (ValueError, IndexError):
        print("invalid choice — defaulting to none (offline-only)")
        provider = "none"
    target = ""
    if provider not in ("none",):
        target = input(
            f"Target for {provider} (folder path, owner/repo, rclone remote"
            " or s3://bucket/prefix): ").strip()
    return provider, target


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    home, force = None, False
    remote_provider, remote_target = None, ""
    i = 0
    while i < len(args):
        if args[i] == "--home" and i + 1 < len(args):
            home, i = args[i + 1], i + 2
        elif args[i] == "--force":
            force, i = True, i + 1
        elif args[i] == "--remote-provider" and i + 1 < len(args):
            remote_provider, i = args[i + 1], i + 2
        elif args[i] == "--remote-target" and i + 1 < len(args):
            remote_target, i = args[i + 1], i + 2
        elif args[i] in ("-h", "--help"):
            print("usage: install.sh [--home DIR] [--force]"
                  " [--remote-provider NAME] [--remote-target TARGET]")
            print("  Creates an isolated social-agent workspace"
                  " (default ~/SocialAgent).")
            print("  Remote providers: " + ", ".join(REMOTE_PROVIDERS))
            print("  Default is none (offline-only); local versioned backups"
                  " always work.")
            return 0
        else:
            print(f"unknown argument {args[i]!r}", file=sys.stderr)
            return 1
    try:
        result = install(home=home, force=force)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"social-agent workspace: {result['home']}")
    for c in result["created"]:
        print(f"  created {c}")
    for k in result["kept"]:
        print(f"  kept    {k}")
    # backup provider setup: explicit flag, interactive tty, else none
    if remote_provider is None and sys.stdin.isatty():
        remote_provider, remote_target = prompt_remote_provider()
    remote_info = setup_remote_backup(
        result["home"], remote_provider or "none", remote_target)
    print()
    print(f"remote backup: {remote_info.get('provider') or 'none (offline-only)'}")
    if remote_info.get("target"):
        print(f"  target: {remote_info['target']}")
    if remote_info.get("encryption"):
        print(f"  {remote_info['encryption']}")
    print()
    print("Next steps:")
    print(f"  export SOCIAL_AGENT_HOME={result['home']}")
    print("  social-agent doctor")
    print("One install = one isolated brain. Run install.sh again on another")
    print("machine (or with --home) for a separate agent installation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
