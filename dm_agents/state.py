"""Persistent state for DM agents.

``last_seen_id`` is tracked per (platform, account, thread) in the shared
memory DB (``dm_agent_state`` table, created by core/memory migration 4).
SQLite on disk survives agent restarts mid-conversation; every write goes
through ``core.memory._after_write`` so the incremental backup captures it.

One row per thread. The pseudo-thread ``__agent__`` holds agent-level
fields (active flag, stop reason, last cycle) for the platform+account.
"""

from core import memory as mem_mod

import re
import time

AGENT_THREAD = "__agent__"

# Older browser reads stored thread ids with a display suffix, e.g.
# "1920160303695716352-2100845624027418624 (Zenas Ayansipe @dagreat00100)",
# while current reads return the bare "1920160303695716352-2100845624027418624".
# The suffix is display decoration, not identity: every state lookup and
# write goes through canonical_thread_id() so both forms resolve to the one
# canonical bare id.
_THREAD_SUFFIX_RE = re.compile(r"^(.*)\s\(([^()]*)\)$")


def canonical_thread_id(thread_id):
    """Strip a trailing " (display name)" suffix to the bare thread id.

    Idempotent: a bare id is returned unchanged. The "__agent__"
    pseudo-thread has no suffix and is unaffected.
    """
    tid = str(thread_id or "")
    m = _THREAD_SUFFIX_RE.match(tid)
    if m and m.group(1):
        return m.group(1)
    return tid


def _ensure_canonical_row(home, platform, account, canonical):
    cx = mem_mod.connect(home)
    try:
        cx.execute(
            "INSERT OR IGNORE INTO dm_agent_state "
            "(platform, account_label, thread_id, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (platform, account, canonical, mem_mod.utcnow()))
        cx.commit()
    finally:
        cx.close()


def _sweep_display_name_aliases(home, platform, account):
    """Delete bare display-name alias rows (e.g. "Zenas Ayansipe @dagreat00100").

    Real platform thread ids never contain "@"; these rows are legacy junk
    from before thread ids were canonicalized. When their cursors go stale
    they cause phantom re-queues of already-handled inbound messages (seen
    live 2026-09-25: 6 phantom reply drafts from one stale alias cursor).
    Only sweeps when at least one canonical (no "@") thread row exists for
    the same (platform, account), so the thread list is never wiped outright.
    Returns True when anything was deleted.
    """
    cx = mem_mod.connect(home)
    try:
        tids = [r["thread_id"] for r in cx.execute(
            "SELECT thread_id FROM dm_agent_state WHERE platform = ? "
            "AND account_label = ? AND thread_id LIKE '%@%'",
            (platform, account)).fetchall()]
        canonical_count = cx.execute(
            "SELECT COUNT(*) FROM dm_agent_state WHERE platform = ? "
            "AND account_label = ? AND thread_id NOT LIKE '%@%' "
            "AND thread_id != '__agent__'",
            (platform, account)).fetchone()[0]
    finally:
        cx.close()
    if not tids or not canonical_count:
        return False
    cx = mem_mod.connect(home)
    try:
        for t in tids:
            cx.execute(
                "DELETE FROM dm_agent_state WHERE platform = ? "
                "AND account_label = ? AND thread_id = ?",
                (platform, account, t))
        cx.commit()
    finally:
        cx.close()
    mem_mod._after_write(home)
    return True


def _sweep_variants(home, platform, account):
    """One-time merge of legacy suffixed thread ids into canonical rows.

    Finds rows whose id carries a display suffix (e.g. "123 (Name
    @handle)"), folds each into its canonical bare-id row — the freshest
    row (max last_inbound_at, ties toward canonical) wins the cursor
    fields — then deletes the variant rows. Also sweeps bare display-name
    alias rows (see _sweep_display_name_aliases). Returns True when anything
    was merged. Cheap no-op once no variants remain.
    """
    cx = mem_mod.connect(home)
    try:
        tids = [r["thread_id"] for r in cx.execute(
            "SELECT thread_id FROM dm_agent_state WHERE platform = ? "
            "AND account_label = ? AND thread_id LIKE '% (%)'",
            (platform, account)).fetchall()]
    finally:
        cx.close()
    groups = {}
    for t in tids:
        c = canonical_thread_id(t)
        if c != t:
            groups.setdefault(c, []).append(t)
    if not groups:
        changed = False
    else:
        changed = False
        for canonical in sorted(groups):
            variants = groups[canonical]
            _ensure_canonical_row(home, platform, account, canonical)
            cx = mem_mod.connect(home)
            try:
                rows = [dict(r) for r in cx.execute(
                    "SELECT * FROM dm_agent_state WHERE platform = ? "
                    "AND account_label = ? AND thread_id IN (%s)"
                    % ",".join("?" * (len(variants) + 1)),
                    (platform, account, canonical, *variants)).fetchall()]
                # The just-inserted canonical placeholder carries defaults
                # (last_inbound_at 0), so any real variant beats it; ties
                # break toward the canonical bare id.
                freshest = max(
                    rows,
                    key=lambda r: (float(r.get("last_inbound_at") or 0.0),
                                   r["thread_id"] == canonical))
                cx.execute(
                    "UPDATE dm_agent_state SET last_seen_id = ?, "
                    "last_inbound_id = ?, last_inbound_at = ?, active = ?, "
                    "stop_reason = ?, last_cycle = ?, last_cycle_ts = ?, "
                    "pending_check = ?, idle_parked = ?, updated_at = ? "
                    "WHERE platform = ? AND account_label = ? AND thread_id = ?",
                    (freshest.get("last_seen_id") or "",
                     freshest.get("last_inbound_id") or "",
                     float(freshest.get("last_inbound_at") or 0.0),
                     freshest.get("active", 1),
                     freshest.get("stop_reason") or "",
                     freshest.get("last_cycle") or "",
                     float(freshest.get("last_cycle_ts") or 0.0),
                     freshest.get("pending_check") or "",
                     freshest.get("idle_parked", 0),
                     mem_mod.utcnow(),
                     platform, account, canonical))
                for v in variants:
                    cx.execute(
                        "DELETE FROM dm_agent_state WHERE platform = ? "
                        "AND account_label = ? AND thread_id = ?",
                        (platform, account, v))
                cx.commit()
                changed = True
            finally:
                cx.close()
    if changed:
        mem_mod._after_write(home)
    if _sweep_display_name_aliases(home, platform, account):
        changed = True
    return changed


def _ensure_row(home, platform, account, thread_id):
    tid = canonical_thread_id(thread_id)
    mem_mod.init_db(home)
    _ensure_canonical_row(home, platform, account, tid)
    _sweep_variants(home, platform, account)


def _update(home, platform, account, thread_id, **fields):
    tid = canonical_thread_id(thread_id)
    _ensure_row(home, platform, account, tid)
    fields["updated_at"] = mem_mod.utcnow()
    cols = ", ".join(f"{k} = ?" for k in fields)
    cx = mem_mod.connect(home)
    try:
        cx.execute(
            f"UPDATE dm_agent_state SET {cols} "
            "WHERE platform = ? AND account_label = ? AND thread_id = ?",
            (*fields.values(), platform, account, tid))
        cx.commit()
    finally:
        cx.close()
    mem_mod._after_write(home)


def get_thread(home, platform, account, thread_id):
    """Return the state row for one thread (dict), creating it if needed.

    The thread id is canonicalized first, so bare and suffixed forms of
    the same conversation resolve to the one merged row.
    """
    tid = canonical_thread_id(thread_id)
    _ensure_row(home, platform, account, tid)
    cx = mem_mod.connect(home)
    try:
        row = cx.execute(
            "SELECT * FROM dm_agent_state WHERE platform = ? "
            "AND account_label = ? AND thread_id = ?",
            (platform, account, tid)).fetchone()
        return dict(row) if row else {}
    finally:
        cx.close()


def list_threads(home, platform, account, include_agent_row=False):
    """All tracked threads for a platform+account.

    Legacy suffixed thread ids are merged into their canonical bare-id
    rows first, so no conversation ever appears twice.
    """
    mem_mod.init_db(home)
    _sweep_variants(home, platform, account)
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
