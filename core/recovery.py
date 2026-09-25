"""Crash recovery: append-only action journal + resume logic.

``<home>/audit/journal.jsonl`` records every acting intent BEFORE it
executes (with an idempotency key) and marks it completed/failed AFTER.
After a crash, ``recover`` replays the journal:

  1. load the latest backup snapshot (context),
  2. list unfinished intents (started, never completed/failed),
  3. VERIFY each one against real state before deciding anything —
     an intent that actually completed is marked completed and SKIPPED,
     never repeated (this is what prevents duplicate posts),
  4. safe local work (renders) can be re-executed with ``--execute``;
     platform-acting intents are NEVER auto-executed — they are reported
     for human re-approval.

Idempotency key: sha256(action_type + target + canonical(payload)).
"""

import hashlib
import json
import os
import random
import shutil
import subprocess
import time
from datetime import datetime, timezone

JOURNAL = os.path.join("audit", "journal.jsonl")
RUNNER_PID = os.path.join("audit", "runner.pid")

STATUSES = ("started", "completed", "failed")


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _journal_path(home):
    return os.path.join(home, JOURNAL)


def _canonical(payload):
    return json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))


def idempotency_key(action_type, target, payload):
    return hashlib.sha256(
        f"{action_type}\n{target}\n{_canonical(payload)}".encode()).hexdigest()


def _read_entries(home):
    p = _journal_path(home)
    if not os.path.exists(p):
        return []
    out = []
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out


def _append(home, entry):
    os.makedirs(os.path.join(home, "audit"), exist_ok=True)
    with open(_journal_path(home), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def begin(home, action_type, target, payload=None, command=None):
    """Log an acting intent BEFORE execution.

    Returns {"duplicate": True, "entry": ...} when the same idempotent
    action already completed — the caller must NOT execute again.
    Otherwise returns {"duplicate": False, "id": ..., "entry": ...}.
    """
    key = idempotency_key(action_type, target, payload)
    for e in _read_entries(home):
        if e.get("idem_key") == key and e.get("status") == "completed":
            return {"duplicate": True, "entry": e, "idem_key": key}
    entry = {
        "id": f"j-{random.randrange(16 ** 8):08x}",
        "ts": utcnow(), "action_type": action_type, "target": target,
        "payload": payload or {}, "payload_hash": hashlib.sha256(
            _canonical(payload).encode()).hexdigest(),
        "idem_key": key, "status": "started", "command": command,
        "result": "", "error": "",
    }
    _append(home, entry)
    return {"duplicate": False, "id": entry["id"], "entry": entry,
            "idem_key": key}


def end(home, entry_id, ok, result="", error=""):
    """Mark a journal entry completed/failed AFTER execution."""
    entries = _read_entries(home)
    found = False
    for e in entries:
        if e.get("id") == entry_id:
            e["status"] = "completed" if ok else "failed"
            e["result"] = result
            e["error"] = error
            e["ended_ts"] = utcnow()
            found = True
            break
    if not found:
        raise KeyError(f"unknown journal entry {entry_id!r}")
    p = _journal_path(home)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")
    os.replace(tmp, p)


def unfinished(home):
    """Intents that started but were never completed/failed (crash residue)."""
    entries = _read_entries(home)
    terminal = {e["idem_key"] for e in entries
                if e.get("status") in ("completed", "failed")}
    return [e for e in entries
            if e.get("status") == "started" and e["idem_key"] not in terminal]


# ------------------------------------------------------------- verification ---

def _verify_publish(home, entry):
    """Did this publish actually happen? Check the approval queue + posts."""
    target = entry.get("target", "")
    # approvals/pending.json: item approved/done referencing the post
    ap = os.path.join(home, "approvals", "pending.json")
    if os.path.exists(ap):
        try:
            with open(ap, encoding="utf-8") as fh:
                items = json.load(fh)
            for it in items:
                ref = it.get("ref") or {}
                if ref.get("id") == target and it.get("status") in (
                        "approved", "done"):
                    return True, f"approval {it['id']} is {it['status']}"
        except (OSError, ValueError):
            pass
    # queue.json: post left draft/queued state
    qp = os.path.join(home, "queue.json")
    if os.path.exists(qp):
        try:
            with open(qp, encoding="utf-8") as fh:
                posts = json.load(fh)
            for q in posts:
                if q.get("id") == target and q.get("status") not in (
                        "draft", "queued"):
                    return True, f"post {target} status={q['status']}"
        except (OSError, ValueError):
            pass
    return False, "no approval/post record shows completion"


def _verify_render(home, entry):
    payload = entry.get("payload") or {}
    out = payload.get("output") or (entry.get("command") or "")
    # command-style entries carry the output path in payload["output"]
    if out and os.path.isfile(out) and os.path.getsize(out) > 0:
        return True, f"output exists ({os.path.getsize(out)} bytes)"
    return False, "output file missing or empty"


def _verify_generic(home, entry):
    return None, "no verifier for this action type — human decision needed"


VERIFIERS = {
    "publish": _verify_publish,
    "publish_post": _verify_publish,
    "render": _verify_render,
}


def verify(home, entry):
    """Check whether an unfinished intent actually completed.

    Returns (completed: True|False|None, reason). None = cannot verify.
    """
    verifier = VERIFIERS.get(entry.get("action_type"), _verify_generic)
    return verifier(home, entry)


# ------------------------------------------------------------ runner lock ---

def mark_runner(home, cmd=""):
    os.makedirs(os.path.join(home, "audit"), exist_ok=True)
    with open(os.path.join(home, RUNNER_PID), "w", encoding="utf-8") as fh:
        json.dump({"pid": os.getpid(), "cmd": cmd, "started_at": utcnow(),
                   "ts": time.time()}, fh)


def clear_runner(home):
    try:
        os.remove(os.path.join(home, RUNNER_PID))
    except OSError:
        pass


def stale_runner(home):
    """Detect an unclean shutdown: pid file exists but process is gone."""
    p = os.path.join(home, RUNNER_PID)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            info = json.load(fh)
        pid = int(info.get("pid", 0))
    except (OSError, ValueError):
        return {"reason": "unreadable pid file"}
    if pid <= 0:
        return {"reason": "bad pid in runner file"}
    try:
        os.kill(pid, 0)
        return None  # process still alive: not stale
    except (OSError, ProcessLookupError):
        return {"reason": f"pid {pid} ({info.get('cmd', '?')}) is gone",
                "info": info}
    except PermissionError:
        return None


# ------------------------------------------------------------------ recover ---

# Action types safe to re-execute locally (no platform side effects).
LOCAL_REEXECUTABLE = {"render"}


def recover(home, execute=False):
    """Replay the journal after a crash. Returns a report dict.

    Never auto-executes platform-acting intents — those are reported for
    human re-approval. Local renders can be re-executed with execute=True.
    """
    from core import backup as backup_mod
    report = {
        "latest_snapshot": backup_mod.latest_id(home),
        "stale_runner": stale_runner(home),
        "resumed": [], "skipped_completed": [], "need_human": [],
        "failed_before": [],
    }
    for entry in unfinished(home):
        done, reason = verify(home, entry)
        item = {"id": entry["id"], "action_type": entry.get("action_type"),
                "target": entry.get("target"), "reason": reason}
        if done is True:
            # It actually completed before the crash: mark + skip. This is
            # the duplicate-post prevention.
            end(home, entry["id"], True,
                result=f"verified post-crash: {reason}")
            report["skipped_completed"].append(item)
        elif done is False:
            if (execute and entry.get("action_type") in LOCAL_REEXECUTABLE
                    and entry.get("command")):
                try:
                    proc = subprocess.run(
                        entry["command"], shell=True,
                        capture_output=True, text=True, timeout=600)
                    ok = proc.returncode == 0
                    end(home, entry["id"], ok,
                        result=proc.stdout[-500:] if ok else "",
                        error=proc.stderr[-500:] if not ok else "")
                    item["re_executed"] = ok
                    report["resumed"].append(item)
                except Exception as e:  # noqa: BLE001 - report, don't crash
                    item["re_execute_error"] = str(e)
                    report["resumed"].append(item)
            else:
                report["resumed"].append(item)
        else:
            report["need_human"].append(item)
    # entries that failed before the crash (for the record)
    for e in _read_entries(home):
        if e.get("status") == "failed":
            report["failed_before"].append(
                {"id": e["id"], "action_type": e.get("action_type"),
                 "target": e.get("target"), "error": e.get("error")})
    clear_runner(home)
    return report


def format_report(report):
    lines = []
    lines.append(f"latest snapshot: {report['latest_snapshot'] or '(none)'}")
    if report["stale_runner"]:
        lines.append(f"unclean shutdown: {report['stale_runner']['reason']}")
    else:
        lines.append("shutdown: clean (no stale runner lock)")
    for s in report["skipped_completed"]:
        lines.append(f"SKIP (already done): {s['action_type']} {s['target']}"
                     f" — {s['reason']}")
    for r in report["resumed"]:
        if r.get("re_executed"):
            lines.append(f"RESUMED+RE-EXECUTED: {r['action_type']}"
                         f" {r['target']} — {r['reason']}")
        elif "re_execute_error" in r:
            lines.append(f"RESUME FAILED: {r['action_type']} {r['target']} —"
                         f" {r['re_execute_error']}")
        else:
            lines.append(f"RESUMABLE: {r['action_type']} {r['target']} —"
                         f" {r['reason']} (re-run with --execute for renders;"
                         " platform actions need human re-approval)")
    for n in report["need_human"]:
        lines.append(f"NEEDS HUMAN: {n['action_type']} {n['target']} —"
                     f" {n['reason']}")
    for f in report["failed_before"]:
        lines.append(f"FAILED BEFORE CRASH: {f['action_type']} {f['target']}"
                     f" — {f['error']}")
    if not (report["skipped_completed"] or report["resumed"] or
            report["need_human"] or report["failed_before"]):
        lines.append("journal is clean: nothing unfinished.")
    return "\n".join(lines)
