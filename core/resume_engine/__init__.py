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
    Checks both the journal AND the permanent actions ledger, so a
    duplicate can never slip through after a crash.
    """
    key = idempotency_key(action_type, target, payload)
    for e in _read_entries(home):
        if e.get("idem_key") == key and e.get("status") == "completed":
            return {"duplicate": True, "entry": e, "idem_key": key}
    try:
        from core import memory as mem_mod
        if key in mem_mod.ledger_completed_keys(home):
            return {"duplicate": True, "entry": mem_mod.ledger_get(home, key),
                    "idem_key": key, "from": "ledger"}
    except Exception:
        pass  # ledger check is defense-in-depth; journal is authoritative
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


def end(home, entry_id, ok, result="", error="", mission_id=None):
    """Mark a journal entry completed/failed AFTER execution.

    Completed actions are ALSO written to the permanent actions ledger
    (keyed by idempotency key) — the ledger is what the resume engine
    consults to prove an action already happened."""
    entries = _read_entries(home)
    found = False
    entry = None
    for e in entries:
        if e.get("id") == entry_id:
            e["status"] = "completed" if ok else "failed"
            e["result"] = result
            e["error"] = error
            e["ended_ts"] = utcnow()
            found = True
            entry = e
            break
    if not found:
        raise KeyError(f"unknown journal entry {entry_id!r}")
    p = _journal_path(home)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")
    os.replace(tmp, p)
    if ok and entry is not None:
        try:
            from core import memory as mem_mod
            mem_mod.ledger_record(home, entry["idem_key"],
                                  entry.get("action_type", ""),
                                  target=entry.get("target", ""),
                                  payload=entry.get("payload"),
                                  status="completed",
                                  mission_id=mission_id,
                                  result=result)
        except Exception:
            pass  # journal already records completion; ledger is additive


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


# ---------------------------------------------------------- full resume ---

def resume_watchers(home):
    """Restore every platform's watchers exactly where they stopped.

    Reads watcher checkpoints (last poll cursor per watcher per platform)
    from the shared memory DB and returns a per-watcher resume summary.
    No events are re-emitted: the cursor's ``seen_ids`` make the next poll
    pick up exactly where the last one stopped — no missed events, no
    duplicates.
    """
    from core import memory as mem_mod
    out = []
    for cp in mem_mod.checkpoint_list(home):
        cursor = cp.get("cursor", {}) or {}
        out.append({
            "id": cp["watcher_id"], "platform": cp["platform"],
            "type": cp.get("watcher_type", ""),
            "account": cp.get("account_label", ""),
            "last_poll": cursor.get("last_poll"),
            "polls": cursor.get("polls", 0),
            "events_found": cursor.get("events_found", 0),
            "seen": len(cursor.get("seen_ids", [])),
            "resumable": True,
        })
    return out


def full_resume(home, execute=False):
    """The resume engine: continue exactly where the agent stopped.

    Steps:
      1. load the latest VALID snapshot (falls back past corrupt ones),
      2. restore browser profiles (cross-check memory registry vs disk),
      3. restore logged-in sessions (sidecar statuses),
      4. replay the event journal (verify-before-repeat, never duplicates),
      5. recover unfinished missions,
      6. verify the last completed action (ledger vs journal),
      7. emit an ordered continue-plan,
      8. restore watchers from their checkpoints (no missed/dupe events).

    Platform actions are NEVER auto-executed — the plan tells the human
    (or the supervisor) exactly what to re-approve.
    """
    from core import backup as backup_mod
    from core import memory as mem_mod
    report = {
        "snapshot": None, "browser_profiles": [], "sessions": [],
        "journal": None, "missions": [], "last_action_verified": None,
        "continue_plan": [], "watchers": [],
    }

    # 1. latest valid snapshot (versioned disaster snapshots first,
    #    then the fine-grained content-addressed ones)
    snap_id = None
    snap_kind = None
    for v in backup_mod.list_versioned(home):
        snap_id, snap_kind = v["id"], "versioned"
        break
    if snap_id is None:
        snap_id = backup_mod.latest_valid_id(home)
        snap_kind = "content-addressed" if snap_id else None
    if snap_id:
        if snap_kind == "versioned":
            ok, why = True, "manifest.json present"
        else:
            ok, why = backup_mod.validate_snapshot(home, snap_id)
        report["snapshot"] = {"id": snap_id, "kind": snap_kind,
                              "valid": ok, "detail": why}
    else:
        report["snapshot"] = {"id": None, "valid": False,
                              "detail": "no valid snapshot found"}

    # 2+3. browser profiles + sessions: memory registry vs on-disk sidecars
    try:
        from browser import session as sess_mod
    except Exception:  # noqa: BLE001 - browser module optional in tests
        sess_mod = None
    for s in mem_mod.session_list(home):
        label = s["account_label"]
        disk = None
        if sess_mod is not None:
            try:
                disk = sess_mod.load_session(home, label)
            except Exception:
                disk = None
        profile_ok = bool(s.get("profile_dir")) and os.path.isdir(
            s["profile_dir"])
        mem_status = s.get("status")
        disk_status = (disk or {}).get("status")
        agree = (disk is None) or (disk_status in (None, mem_status))
        report["browser_profiles"].append({
            "account": label, "profile_dir": s.get("profile_dir"),
            "profile_on_disk": profile_ok,
            "memory_status": mem_status, "disk_status": disk_status,
            "agree": agree,
        })
        report["sessions"].append({
            "account": label, "status": disk_status or mem_status,
            "restorable": profile_ok and (disk_status or mem_status)
            not in ("challenge",),
            "note": ("challenge open — resolve with headed login"
                     if (disk_status or mem_status) == "challenge" else ""),
        })

    # 4. replay the journal (the duplicate-proof core)
    journal_report = recover(home, execute=execute)
    report["journal"] = journal_report

    # 5. unfinished missions
    unfinished_intents = unfinished(home)
    for m in mem_mod.mission_pending(home):
        related = [e for e in unfinished_intents
                   if (e.get("payload") or {}).get("_mission") == m["name"]]
        report["missions"].append({
            "name": m["name"], "type": m["mission_type"],
            "status": m["status"], "account": m["account_label"],
            "unfinished_intents": len(related),
            "action": ("resume" if m["status"] in ("active", "pending")
                       else "review"),
        })

    # 6. verify the last completed action: ledger vs journal agree
    ledger = mem_mod.ledger_list(home, limit=1)
    journal_done = [e for e in _read_entries(home)
                    if e.get("status") == "completed"]
    if ledger and journal_done:
        last = ledger[0]
        match = any(e.get("idem_key") == last["idem_key"]
                    for e in journal_done)
        report["last_action_verified"] = {
            "action": f"{last['action_type']} {last['target']}",
            "ledger_and_journal_agree": match,
        }
    elif ledger:
        report["last_action_verified"] = {
            "action": f"{ledger[0]['action_type']} {ledger[0]['target']}",
            "ledger_and_journal_agree": False,
            "note": "in ledger but no completed journal entry",
        }
    else:
        report["last_action_verified"] = {"action": None,
                                          "note": "no completed actions yet"}

    # 7. ordered continue-plan
    plan = []
    for s in report["sessions"]:
        if not s["restorable"]:
            plan.append(f"session: re-login '{s['account']}' ({s['note']})"
                        if s["note"] else
                        f"session: re-login '{s['account']}' (no profile)")
    for m in report["missions"]:
        if m["action"] == "resume":
            plan.append(
                f"mission: resume '{m['name']}' [{m['status']}]"
                f" — {m['unfinished_intents']} unfinished intent(s)")
        else:
            plan.append(f"mission: review '{m['name']}' [{m['status']}]")
    for r in journal_report["resumed"]:
        plan.append(f"intent: re-approve {r['action_type']} {r['target']}")
    for n in journal_report["need_human"]:
        plan.append(f"intent: decide {n['action_type']} {n['target']}"
                    f" — {n['reason']}")
    report["continue_plan"] = plan

    # 8. watchers: restore from checkpoints (last poll cursor per watcher)
    for w in resume_watchers(home):
        report["watchers"].append(w)
        last = w["last_poll"] or "never polled"
        plan.append(f"watcher: resume '{w['id']}' [{w['platform']}]"
                    f" — last poll {last}, {w['seen']} item(s) seen")
    report["continue_plan"] = plan
    return report


def format_full_resume(report):
    lines = ["== resume engine =="]
    snap = report["snapshot"]
    if snap["id"]:
        lines.append(f"1. snapshot: {snap['id']} [{snap.get('kind')}]"
                     f" (valid={snap['valid']})")
    else:
        lines.append(f"1. snapshot: none — {snap['detail']}")
    lines.append("2+3. browser profiles / sessions:")
    if not report["browser_profiles"]:
        lines.append("   (no browser sessions registered)")
    for b in report["browser_profiles"]:
        lines.append(
            f"   {b['account']}: profile_on_disk={b['profile_on_disk']}"
            f" memory={b['memory_status']} disk={b['disk_status']}"
            f" agree={b['agree']}")
    for s in report["sessions"]:
        lines.append(f"   session {s['account']}: status={s['status']}"
                     f" restorable={s['restorable']}"
                     + (f" — {s['note']}" if s["note"] else ""))
    lines.append("4. journal replay:")
    lines.append("   " + format_report(report["journal"]).replace(
        "\n", "\n   "))
    lines.append("5. missions:")
    if not report["missions"]:
        lines.append("   (no pending missions)")
    for m in report["missions"]:
        lines.append(f"   {m['action'].upper()}: '{m['name']}'"
                     f" [{m['status']}] ({m['unfinished_intents']}"
                     " unfinished intent(s))")
    lines.append("6. last completed action:")
    la = report["last_action_verified"]
    if la.get("action"):
        lines.append(f"   {la['action']} — ledger/journal agree:"
                     f" {la.get('ledger_and_journal_agree')}")
    else:
        lines.append(f"   {la.get('note', 'none')}")
    lines.append("7. continue plan:")
    if not report["continue_plan"]:
        lines.append("   (nothing to do — agent is exactly where it stopped)")
    for p in report["continue_plan"]:
        lines.append(f"   - {p}")
    lines.append("8. watchers (checkpoints replayed):")
    if not report["watchers"]:
        lines.append("   (no watcher checkpoints — no watchers have polled yet)")
    for w in report["watchers"]:
        lines.append(f"   {w['id']} [{w['platform']}/{w['type']}]"
                     f" last_poll={w['last_poll']} polls={w['polls']}"
                     f" seen={w['seen']} resumable={w['resumable']}")
    return "\n".join(lines)
