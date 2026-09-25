"""Security audit: scan state for secrets + report hardening status (stdlib)."""

import json
import os

from . import secrets as secrets_mod

# state files worth scanning for accidentally stored secrets
SCAN_FILES = ("queue.json", "actions.json", "profiles.json", "research.json")


def security_audit(home):
    """Return a list of {check, status, detail}.

    status: "pass" | "warn" | "fail".
    """
    results = []

    # 1. scan state files for secret-shaped content
    hits = []
    for name in SCAN_FILES:
        p = os.path.join(home, name)
        if not os.path.exists(p):
            continue
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        blob = json.dumps(data)
        found, pat = secrets_mod.contains_secret(blob)
        if found:
            hits.append(f"{name}: {pat}")
    results.append({
        "check": "no secrets in drafts/actions/profiles",
        "status": "fail" if hits else "pass",
        "detail": "; ".join(hits) if hits else "clean",
    })

    # 2. scan events log lightly (sample, not the whole file)
    p = os.path.join(home, "events.jsonl")
    ev_hits = 0
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if i > 5000:
                    break
                found, _ = secrets_mod.contains_secret(line)
                if found:
                    ev_hits += 1
    results.append({
        "check": "no secrets in event log (sampled)",
        "status": "fail" if ev_hits else "pass",
        "detail": f"{ev_hits} suspicious lines" if ev_hits else "clean",
    })

    # 3. human-only hardening items (reminders, not checks)
    for item in ("2FA enabled on all accounts",
                 "recovery codes stored offline",
                 "third-party app access reviewed",
                 "security watcher running per account"):
        on = item == "security watcher running per account" and _watcher_running(home)
        results.append({
            "check": item,
            "status": "pass" if on else "warn",
            "detail": "running" if on else "human action required — see security/checklist.md",
        })
    return results


def _watcher_running(home):
    p = os.path.join(home, "watchers.json")
    if not os.path.exists(p):
        return False
    try:
        with open(p, encoding="utf-8") as fh:
            reg = json.load(fh)
    except (OSError, ValueError):
        return False
    return any(r.get("type") == "security" and r.get("enabled") for r in reg.values())
