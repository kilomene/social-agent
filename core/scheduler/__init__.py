"""Scheduler: a shared core service (single instance for every platform).

All scheduler state lives in the memory DB (``scheduler_jobs`` table), so
schedules survive restarts and are covered by backups like everything else.

Job kinds:
  once      — run once at an ISO timestamp (spec=run_at)
  interval  — run every N seconds (spec=seconds)
  daily     — run daily at HH:MM (spec="HH:MM")

``tick(home)`` finds due, enabled jobs and records an idempotency-keyed
intent in the action journal for each one — so a crash between tick and
execution can never double-fire a job. The journal entry is the actual
work order; ``mark_ran`` advances the job's next run after it executes.

Typical jobs: watcher polling sweeps, mission schedules, posting
schedules, backup snapshots, remote backup syncs (the sync itself stays
manual/consented — the job only *proposes* it).
"""

from datetime import datetime, timezone

from core import memory as mem_mod
from core import recovery as rec_mod


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# Re-export the memory-layer job API so callers only import this module.
add = mem_mod.sched_add
get = mem_mod.sched_get
list_jobs = mem_mod.sched_list
set_job = mem_mod.sched_set
mark_ran = mem_mod.sched_mark_ran
due = mem_mod.sched_due


def tick(home, now_iso=None):
    """Fire due jobs: journal one intent per job (idempotency-keyed).

    Returns a list of {job, intent, duplicate} dicts. Duplicates are
    detected via the idempotency key, so re-ticking is always safe.
    """
    now_iso = now_iso or utcnow()
    fired = []
    for job in mem_mod.sched_due(home, now_iso):
        payload = dict(job.get("payload") or {})
        payload["_scheduler_job"] = job["name"]
        payload["_fired_at"] = now_iso
        key = rec_mod.idempotency_key(
            "scheduler_fire", f"job:{job['name']}", {"slot": now_iso})
        began = rec_mod.begin(home, "scheduler_fire",
                              f"job:{job['name']}", payload)
        if began.get("duplicate"):
            fired.append({"job": job["name"], "duplicate": True,
                          "idem_key": key})
            continue
        mem_mod.sched_mark_ran(home, job["name"])
        fired.append({"job": job["name"], "duplicate": False,
                      "intent_id": began["id"], "idem_key": began["idem_key"]})
    return fired


def tick_summary(home, now_iso=None):
    fired = tick(home, now_iso)
    new = [f for f in fired if not f["duplicate"]]
    dup = [f for f in fired if f["duplicate"]]
    lines = [f"scheduler tick at {now_iso or utcnow()}:"]
    for f in new:
        lines.append(f"  FIRED: {f['job']} (intent {f['intent_id']})")
    for f in dup:
        lines.append(f"  SKIP (already fired): {f['job']}")
    if not fired:
        lines.append("  no jobs due")
    return "\n".join(lines)


def install_default_jobs(home):
    """Seed the standard housekeeping jobs (idempotent)."""
    mem_mod.sched_add(home, "memory-healthcheck", "interval", "3600",
                      {"action": "session_health_sweep"})
    mem_mod.sched_add(home, "daily-backup", "daily", "03:00",
                      {"action": "versioned_snapshot",
                       "note": "automatic daily snapshot"})
    return mem_mod.sched_list(home)
