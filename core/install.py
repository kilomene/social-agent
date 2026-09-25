"""Installer: create one isolated agent workspace ("its own brain").

Creates (default ``~/SocialAgent/``, override with --home or
$SOCIAL_AGENT_HOME)::

    memory.db            permanent SQLite memory (schema initialized)
    backups/             manifests/ + blobs/ + restore_staging/
    audit/               journal.jsonl + runner.pid live here
    projects/            Kdenlive/Shotcut projects + render work dirs
    accounts/            per-account files (browser profiles, personas)
    cache/               disposable downloads / temp media

Idempotent: re-running against an existing install only tops up missing
pieces. Refuses to touch an existing non-empty directory without --force.
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
               "accounts", "cache")

VERSION = "0.1.0"


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


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    home, force = None, False
    i = 0
    while i < len(args):
        if args[i] == "--home" and i + 1 < len(args):
            home, i = args[i + 1], i + 2
        elif args[i] == "--force":
            force, i = True, i + 1
        elif args[i] in ("-h", "--help"):
            print("usage: install.sh [--home DIR] [--force]")
            print("  Creates an isolated social-agent workspace"
                  " (default ~/SocialAgent).")
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
    print()
    print("Next steps:")
    print(f"  export SOCIAL_AGENT_HOME={result['home']}")
    print("  social-agent doctor")
    print("One install = one isolated brain. Run install.sh again on another")
    print("machine (or with --home) for a separate agent installation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
