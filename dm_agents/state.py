"""Persistent state for DM agents.

``last_seen_id`` is tracked per (platform, account, thread) in the shared
memory DB (``dm_agent_state`` table, created by core/memory migration 4).
SQLite on disk survives agent restarts mid-conversation; every write goes
through ``core.memory._after_write`` so the incremental backup captures it.

One row per thread. The pseudo-thread ``__agent__`` holds agent-level
fields (active flag, stop reason, last cycle) for the platform+account.
"""

from core import memory as mem_mod

import time

AGENT_THREAD = "__agent__"


def _ensure_row(home, platform, account, thread_id):
    mem_mod.init_db(home)
    cx = mem_mod.connect(home)
    try:
        cx.execute(
            "INSERT OR IGNORE INTO dm_agent_state "
            "(platform, account_label, thread_id, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (platform, account, thread_id, mem_mod.utcnow()))
        cx.commit()
    finally:
        cx.close()


def _update(home, platform, account, thread_id, **fields):
    _ensure_row(home, platform, account, thread_id)
    fields["updated_at"] = mem_mod.utcnow()
    cols = ", ".join(f"{k} = ?" for k in fields)
    cx = mem_mod.connect(home)
    try:
        cx.execute(
            f"UPDATE dm_agent_state SET {cols} "
            "WHERE platform = ? AND account_label = ? AND thread_id = ?",
            (*fields.values(), platform, account, thread_id))
        cx.commit()
    finally:
        cx.close()
    mem_mod._after_write(home)


def get_thread(home, platform, account, thread_id):
    """Return the state row for one thread (dict), creating it if needed."""
    _ensure_row(home, platform, account, thread_id)
    cx = mem_mod.connect(home)
    try:
        row = cx.execute(
            "SELECT * FROM dm_agent_state WHERE platform = ? "
            "AND account_label = ? AND thread_id = ?",
            (platform, account, thread_id)).fetchone()
        return dict(row) if row else {}
    finally:
        cx.close()


def list_threads(home, platform, account, include_agent_row=False):
    """All tracked threads for a platform+account."""
    mem_mod.init_db(home)
    cx = mem_mod.connect(home)
    try:
        rows = cx.execute(
            "SELECT * FROM dm_agent_state WHERE platform = ? "
            "AND account_label = ? ORDER BY thread_id",
            (platform, account)).fetchall()
    finally:
        cx.close()
    out = [dict(r) for r in rows]
    if not include_agent_row:
        out = [r for r in out if r["thread_id"] != AGENT_THREAD]
    return out


def set_last_seen(home, platform, account, thread_id, last_seen_id,
                  last_inbound_id="", last_inbound_ts=0.0):
    """Advance the cursor after a thread has been processed."""
    _update(home, platform, account, thread_id,
            last_seen_id=last_seen_id or "",
            last_inbound_id=last_inbound_id or "",
            last_inbound_at=float(last_inbound_ts or 0.0),
            idle_parked=0)


def get_last_seen(home, platform, account, thread_id):
    return get_thread(home, platform, account, thread_id).get("last_seen_id") or ""


# ---- agent-level lifecycle (stored on the __agent__ pseudo-thread) ----

def agent_status(home, platform, account):
    row = get_thread(home, platform, account, AGENT_THREAD)
    return {
        "active": bool(row.get("active", 1)),
        "stop_reason": row.get("stop_reason") or "",
        "last_cycle": row.get("last_cycle") or "",
        "last_cycle_ts": row.get("last_cycle_ts") or 0.0,
        "pending_check": row.get("pending_check") or "",
    }


def set_active(home, platform, account, active, reason=""):
    _update(home, platform, account, AGENT_THREAD,
            active=1 if active else 0, stop_reason=reason or "")


def record_cycle(home, platform, account, label=""):
    _update(home, platform, account, AGENT_THREAD,
            last_cycle=label or mem_mod.utcnow(),
            last_cycle_ts=time.time())


def set_pending_check(home, platform, account, ticket_id):
    _update(home, platform, account, AGENT_THREAD,
            pending_check=ticket_id or "")


def get_pending_check(home, platform, account):
    return (get_thread(home, platform, account, AGENT_THREAD)
            .get("pending_check") or "")


def park_idle_thread(home, platform, account, thread_id, reason):
    _update(home, platform, account, thread_id,
            idle_parked=1, stop_reason=reason or "")


def unpark_thread(home, platform, account, thread_id):
    _update(home, platform, account, thread_id,
            idle_parked=0, stop_reason="")
