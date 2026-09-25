"""Permanent memory: the agent's brain as a SQLite database.

``<home>/memory.db`` holds everything the agent must never lose:
accounts, brand voice, people (followers/conversations), campaigns,
posting schedule, content, content performance, CEO decisions, SOPs,
and a relationship graph (brand owns account, follower is a frequent
customer, hashtag performs well on Fridays, video belongs to campaign).

Stdlib only (sqlite3). Postgres is the documented scale-up path
(see core/POSTGRES.md); the schema ports 1:1.

Every write goes through this module so two things stay true:
  1. schema migrations run automatically (schema_migrations table),
  2. memory mutations trigger an incremental backup (backup.py).
"""

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone

DB_NAME = "memory.db"
SCHEMA_VERSION = 3

# ---------------------------------------------------------------- schema ---

_MIGRATIONS = {
    1: """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS accounts (
    label TEXT PRIMARY KEY, platform TEXT NOT NULL, handle TEXT,
    brand TEXT, status TEXT DEFAULT 'active', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS brand_voice (
    account_label TEXT PRIMARY KEY, tone_profile TEXT,
    banned_terms_json TEXT DEFAULT '[]', dos_json TEXT DEFAULT '[]',
    donts_json TEXT DEFAULT '[]', updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS people (
    account_label TEXT NOT NULL, handle TEXT NOT NULL,
    first_seen TEXT, last_seen TEXT,
    interactions_json TEXT DEFAULT '{}', score REAL DEFAULT 0,
    sentiment REAL, tags_json TEXT DEFAULT '[]',
    notes_json TEXT DEFAULT '[]', conversations_json TEXT DEFAULT '[]',
    last_text TEXT DEFAULT '', sentiments_json TEXT DEFAULT '[]',
    PRIMARY KEY (account_label, handle));
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
    account_label TEXT, goal TEXT, starts_at TEXT, ends_at TEXT,
    status TEXT DEFAULT 'active');
CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT, account_label TEXT,
    action_type TEXT, payload_json TEXT DEFAULT '{}', run_at TEXT,
    recurrence TEXT, status TEXT DEFAULT 'pending');
CREATE TABLE IF NOT EXISTS content (
    id INTEGER PRIMARY KEY AUTOINCREMENT, account_label TEXT,
    campaign_id INTEGER, kind TEXT, title TEXT, file_path TEXT,
    caption TEXT, posted_at TEXT, platform_post_id TEXT,
    status TEXT DEFAULT 'draft');
CREATE TABLE IF NOT EXISTS performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT, content_id INTEGER,
    platform TEXT, metric TEXT, value REAL, sampled_at TEXT);
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, made_by TEXT, summary TEXT,
    rationale TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sops (
    id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, body_md TEXT,
    version INTEGER DEFAULT 1, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_type TEXT NOT NULL, subject_id TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_type TEXT NOT NULL, object_id TEXT NOT NULL,
    meta_json TEXT DEFAULT '{}', created_at TEXT NOT NULL,
    UNIQUE (subject_type, subject_id, predicate, object_type, object_id));
""",
    # v10: memory becomes the center of the system. New tables:
    #   conversations   — agent<->user turns worth remembering
    #   browser_sessions— registry of host-browser sessions per account
    #                     (which host agent + live session executed what;
    #                     written when tickets are claimed/fulfilled)
    #   missions        — pending + active + completed mission records
    #   actions_ledger  — every completed action, keyed by idempotency key
    #   scheduler_jobs  — scheduler state (survives restarts)
    #   analytics       — per-platform performance rollups
    # brand_voice gains learned examples + style rules (deepened voice).
    2: """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL, role TEXT NOT NULL,
    account_label TEXT DEFAULT '', mission_id INTEGER,
    kind TEXT DEFAULT 'chat', text TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS browser_sessions (
    account_label TEXT PRIMARY KEY, identity_id TEXT DEFAULT '',
    profile_dir TEXT NOT NULL, platform TEXT NOT NULL,
    status TEXT DEFAULT 'new', last_health_check TEXT,
    challenge TEXT, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS missions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE, mission_type TEXT DEFAULT 'custom',
    account_label TEXT DEFAULT '', status TEXT DEFAULT 'pending',
    spec_json TEXT DEFAULT '{}', result_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS actions_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idem_key TEXT NOT NULL UNIQUE, action_type TEXT NOT NULL,
    target TEXT DEFAULT '', payload_json TEXT DEFAULT '{}',
    status TEXT DEFAULT 'completed', mission_id INTEGER,
    created_at TEXT NOT NULL, completed_at TEXT,
    result TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS scheduler_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE, kind TEXT NOT NULL,
    spec TEXT DEFAULT '', payload_json TEXT DEFAULT '{}',
    status TEXT DEFAULT 'enabled',
    last_run TEXT, next_run TEXT, run_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL, account_label TEXT DEFAULT '',
    metric TEXT NOT NULL, value REAL NOT NULL,
    period TEXT DEFAULT '', sampled_at TEXT NOT NULL);
ALTER TABLE brand_voice ADD COLUMN examples_json TEXT DEFAULT '[]';
ALTER TABLE brand_voice ADD COLUMN style_rules_json TEXT DEFAULT '[]';
ALTER TABLE brand_voice ADD COLUMN last_trained TEXT;
""",
    3: """
CREATE TABLE IF NOT EXISTS watcher_checkpoints (
    watcher_id TEXT PRIMARY KEY, platform TEXT NOT NULL,
    watcher_type TEXT DEFAULT '', account_label TEXT DEFAULT '',
    cursor_json TEXT DEFAULT '{}', updated_at TEXT NOT NULL);
""",
}

# Tables hashed for incremental backups (stable order).
HASHED_TABLES = ("accounts", "brand_voice", "people", "campaigns", "schedule",
                 "content", "performance", "decisions", "sops", "relations",
                 "conversations", "browser_sessions", "missions",
                 "actions_ledger", "scheduler_jobs", "analytics",
                 "watcher_checkpoints")


def db_path(home):
    return os.path.join(home, DB_NAME)


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(home):
    os.makedirs(home, exist_ok=True)
    cx = sqlite3.connect(db_path(home))
    cx.row_factory = sqlite3.Row
    return cx


def schema_version(home):
    cx = connect(home)
    try:
        try:
            row = cx.execute(
                "SELECT MAX(version) AS v FROM schema_migrations").fetchone()
        except sqlite3.OperationalError:
            return 0
        return row["v"] or 0
    finally:
        cx.close()


def init_db(home):
    """Create/migrate the database. Idempotent."""
    cx = connect(home)
    try:
        cur = max(_MIGRATIONS)
        have = schema_version(home)
        for v in range(have + 1, cur + 1):
            cx.executescript(_MIGRATIONS[v])
            cx.execute(
                "INSERT INTO schema_migrations (version, applied_at)"
                " VALUES (?, ?)", (v, utcnow()))
            cx.commit()
    finally:
        cx.close()
    return db_path(home)


def _after_write(home):
    """Incremental backup hook: every memory mutation snapshots the DB."""
    try:
        from core import backup as backup_mod
        backup_mod.snapshot_memory_incremental(home)
    except Exception:
        # Memory must never fail because backup hiccuped.
        pass


def _row_to_dict(row):
    return dict(row) if row is not None else None


# ---------------------------------------------------------------- accounts ---

def upsert_account(home, label, platform, handle="", brand="", status="active"):
    init_db(home)
    cx = connect(home)
    try:
        cx.execute(
            "INSERT INTO accounts (label, platform, handle, brand, status,"
            " created_at) VALUES (?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(label) DO UPDATE SET platform=excluded.platform,"
            " handle=excluded.handle, brand=excluded.brand,"
            " status=excluded.status",
            (label, platform, handle, brand, status, utcnow()))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return get_account(home, label)


def get_account(home, label):
    init_db(home)
    cx = connect(home)
    try:
        return _row_to_dict(cx.execute(
            "SELECT * FROM accounts WHERE label = ?", (label,)).fetchone())
    finally:
        cx.close()


def list_accounts(home):
    init_db(home)
    cx = connect(home)
    try:
        return [_row_to_dict(r) for r in
                cx.execute("SELECT * FROM accounts ORDER BY label")]
    finally:
        cx.close()


# --------------------------------------------------------------- brand voice ---

def set_brand_voice(home, account_label, tone_profile="", banned=(),
                    dos=(), donts=()):
    init_db(home)
    cx = connect(home)
    try:
        cx.execute(
            "INSERT INTO brand_voice (account_label, tone_profile,"
            " banned_terms_json, dos_json, donts_json, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(account_label) DO UPDATE SET"
            " tone_profile=excluded.tone_profile,"
            " banned_terms_json=excluded.banned_terms_json,"
            " dos_json=excluded.dos_json, donts_json=excluded.donts_json,"
            " updated_at=excluded.updated_at",
            (account_label, tone_profile, json.dumps(list(banned)),
             json.dumps(list(dos)), json.dumps(list(donts)), utcnow()))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return get_brand_voice(home, account_label)


def get_brand_voice(home, account_label):
    init_db(home)
    cx = connect(home)
    try:
        return _row_to_dict(cx.execute(
            "SELECT * FROM brand_voice WHERE account_label = ?",
            (account_label,)).fetchone())
    finally:
        cx.close()


# ------------------------------------------------------------------ people ---

# Interaction weights (same scale as the legacy people/db.py).
WEIGHTS = {"comment": 3, "like": 1, "dm": 5, "follow": 4, "mention": 2}
KINDS = tuple(WEIGHTS)


def _person_key(handle):
    return str(handle or "unknown").lower().lstrip("@")


def _blank_person(account_label, handle):
    now = utcnow()
    return {
        "account_label": account_label, "handle": _person_key(handle),
        "first_seen": now, "last_seen": now,
        "interactions_json": json.dumps({k: 0 for k in KINDS}),
        "score": 0.0, "sentiment": None, "tags_json": "[]",
        "notes_json": "[]", "conversations_json": "[]", "last_text": "",
        "sentiments_json": "[]",
    }


def _decode_person(row):
    d = _row_to_dict(row)
    if d is None:
        return None
    d["counts"] = json.loads(d.pop("interactions_json") or "{}")
    d["tags"] = json.loads(d.pop("tags_json") or "[]")
    d["notes"] = json.loads(d.pop("notes_json") or "[]")
    d["conversations"] = json.loads(d.pop("conversations_json") or "[]")
    d["sentiments"] = json.loads(d.pop("sentiments_json") or "[]")
    return d


def _encode_counts(counts):
    return json.dumps({k: int(counts.get(k, 0)) for k in KINDS})


def upsert_interaction(home, account_label, handle, kind, text=None,
                       sentiment=None, summary=None):
    """Record one interaction; returns the decoded person record."""
    if kind not in KINDS:
        raise ValueError(f"bad interaction kind {kind!r}")
    init_db(home)
    migrate_people_json(home)
    cx = connect(home)
    try:
        key = _person_key(handle)
        row = cx.execute(
            "SELECT * FROM people WHERE account_label = ? AND handle = ?",
            (account_label, key)).fetchone()
        rec = _decode_person(row) if row else None
        if rec is None:
            blank = _blank_person(account_label, key)
            cx.execute(
                "INSERT INTO people (account_label, handle, first_seen,"
                " last_seen, interactions_json) VALUES (?, ?, ?, ?, ?)",
                (account_label, key, blank["first_seen"], blank["last_seen"],
                 blank["interactions_json"]))
            cx.commit()
            rec = _decode_person(cx.execute(
                "SELECT * FROM people WHERE account_label = ? AND handle = ?",
                (account_label, key)).fetchone())
        counts = rec["counts"]
        counts[kind] = counts.get(kind, 0) + 1
        score = sum(WEIGHTS[k] * counts.get(k, 0) for k in KINDS)
        sentiments = rec["sentiments"]
        if isinstance(sentiment, (int, float)):
            sentiments = (sentiments + [round(sentiment, 3)])[-50:]
        conversations = rec["conversations"]
        if kind == "dm" and (summary or text):
            conversations = (conversations + [{
                "ts": utcnow(), "kind": "dm",
                "summary": (summary or str(text))[:300]}])[-100:]
        cx.execute(
            "UPDATE people SET last_seen = ?, interactions_json = ?,"
            " score = ?, sentiment = ?, sentiments_json = ?,"
            " conversations_json = ?, last_text = ?"
            " WHERE account_label = ? AND handle = ?",
            (utcnow(), _encode_counts(counts), score,
             round(sum(sentiments) / len(sentiments), 3) if sentiments else None,
             json.dumps(sentiments), json.dumps(conversations),
             str(text)[:300] if text else rec["last_text"],
             account_label, key))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return get_person(home, account_label, handle)


def get_person(home, account_label, handle):
    init_db(home)
    migrate_people_json(home)
    cx = connect(home)
    try:
        return _decode_person(cx.execute(
            "SELECT * FROM people WHERE account_label = ? AND handle = ?",
            (account_label, _person_key(handle))).fetchone())
    finally:
        cx.close()


def ensure_person(home, account_label, handle):
    rec = get_person(home, account_label, handle)
    if rec is None:
        upsert_interaction(home, account_label, handle, "mention")
        # a bare mention shouldn't count as a real interaction: zero it
        cx = connect(home)
        try:
            cx.execute(
                "UPDATE people SET interactions_json = ?, score = 0"
                " WHERE account_label = ? AND handle = ?",
                (_encode_counts({}), account_label, _person_key(handle)))
            cx.commit()
        finally:
            cx.close()
        rec = get_person(home, account_label, handle)
    return rec


def top_people(home, account_label, n=10):
    init_db(home)
    migrate_people_json(home)
    cx = connect(home)
    try:
        rows = cx.execute(
            "SELECT * FROM people WHERE account_label = ?"
            " ORDER BY score DESC, last_seen DESC LIMIT ?",
            (account_label, n)).fetchall()
    finally:
        cx.close()
    out = []
    for r in rows:
        d = _decode_person(r)
        out.append((d["handle"], d["score"], d))
    return out


def add_person_note(home, account_label, handle, text):
    ensure_person(home, account_label, handle)
    cx = connect(home)
    try:
        row = cx.execute(
            "SELECT notes_json FROM people WHERE account_label = ?"
            " AND handle = ?", (account_label, _person_key(handle))).fetchone()
        notes = json.loads(row["notes_json"] or "[]")
        notes.append({"ts": utcnow(), "text": text})
        cx.execute(
            "UPDATE people SET notes_json = ? WHERE account_label = ?"
            " AND handle = ?", (json.dumps(notes), account_label,
                                _person_key(handle)))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return get_person(home, account_label, handle)


def add_person_tag(home, account_label, handle, tag):
    ensure_person(home, account_label, handle)
    tag = tag.strip().lower().replace(" ", "-")
    cx = connect(home)
    try:
        row = cx.execute(
            "SELECT tags_json FROM people WHERE account_label = ?"
            " AND handle = ?", (account_label, _person_key(handle))).fetchone()
        tags = json.loads(row["tags_json"] or "[]")
        if tag and tag not in tags:
            tags.append(tag)
        cx.execute(
            "UPDATE people SET tags_json = ? WHERE account_label = ?"
            " AND handle = ?", (json.dumps(tags), account_label,
                                _person_key(handle)))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return get_person(home, account_label, handle)


def remove_person_tag(home, account_label, handle, tag):
    tag = tag.strip().lower().replace(" ", "-")
    cx = connect(home)
    try:
        row = cx.execute(
            "SELECT tags_json FROM people WHERE account_label = ?"
            " AND handle = ?", (account_label, _person_key(handle))).fetchone()
        if row is None:
            raise KeyError(f"unknown person {handle!r}")
        tags = json.loads(row["tags_json"] or "[]")
        if tag in tags:
            tags.remove(tag)
        cx.execute(
            "UPDATE people SET tags_json = ? WHERE account_label = ?"
            " AND handle = ?", (json.dumps(tags), account_label,
                                _person_key(handle)))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return get_person(home, account_label, handle)


def person_score(counts):
    return sum(WEIGHTS.get(k, 0) * counts.get(k, 0) for k in WEIGHTS)


def qualifies_as_top_fan(home, account_label, handle):
    rec = get_person(home, account_label, handle)
    if not rec:
        return False
    counts = rec["counts"]
    return (rec["score"] >= 15 and
            (counts.get("comment", 0) + counts.get("like", 0)) >= 5)


def is_top_fan(home, account_label, handle):
    rec = get_person(home, account_label, handle)
    return bool(rec) and "top-fan" in (rec.get("tags") or [])


# ------------------------------------------------------- legacy JSON import ---

_LEGACY_DIR = "people"


def migrate_people_json(home):
    """One-time import of the legacy people/*.json store into SQLite.

    After a successful import the JSON files are moved aside to
    ``people_legacy_<timestamp>/`` so the migration never runs twice.
    Safe to call on every people access.
    """
    legacy = os.path.join(home, _LEGACY_DIR)
    if not os.path.isdir(legacy):
        return {"migrated": 0}
    files = [f for f in os.listdir(legacy) if f.endswith(".json")]
    if not files:
        return {"migrated": 0}
    init_db(home)
    cx = connect(home)
    migrated = 0
    try:
        for fname in sorted(files):
            account_label = fname[:-5]  # account label was the filename
            try:
                with open(os.path.join(legacy, fname),
                          encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, ValueError):
                continue
            for key, rec in (data or {}).items():
                handle = rec.get("handle", key)
                counts = rec.get("counts", {}) or {}
                score = sum(WEIGHTS.get(k, 0) * int(counts.get(k, 0))
                            for k in KINDS)
                sents = rec.get("sentiments") or []
                cx.execute(
                    "INSERT INTO people (account_label, handle, first_seen,"
                    " last_seen, interactions_json, score, sentiment,"
                    " tags_json, notes_json, conversations_json, last_text,"
                    " sentiments_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,"
                    " ?, ?, ?)"
                    " ON CONFLICT(account_label, handle) DO NOTHING",
                    (account_label, _person_key(handle),
                     rec.get("first_seen"), rec.get("last_seen"),
                     _encode_counts(counts), score,
                     round(sum(sents) / len(sents), 3) if sents else None,
                     json.dumps(rec.get("tags") or []),
                     json.dumps(rec.get("notes") or []),
                     json.dumps(rec.get("conversations") or []),
                     rec.get("last_text") or "",
                     json.dumps(sents)))
                migrated += 1
        cx.commit()
    finally:
        cx.close()
    # Move the legacy files aside (never delete user data silently).
    import time as _time
    dest = os.path.join(
        home, f"people_legacy_{int(_time.time())}")
    os.makedirs(dest, exist_ok=True)
    for fname in files:
        try:
            os.replace(os.path.join(legacy, fname),
                       os.path.join(dest, fname))
        except OSError:
            pass
    try:
        os.rmdir(legacy)
    except OSError:
        pass
    return {"migrated": migrated, "archived_to": dest}


# ---------------------------------------------------------------- campaigns ---

def create_campaign(home, name, account_label="", goal="", starts_at="",
                    ends_at=""):
    init_db(home)
    cx = connect(home)
    try:
        cur = cx.execute(
            "INSERT INTO campaigns (name, account_label, goal, starts_at,"
            " ends_at, status) VALUES (?, ?, ?, ?, ?, 'active')",
            (name, account_label, goal, starts_at, ends_at))
        cid = cur.lastrowid
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return cid


def list_campaigns(home, status=None):
    init_db(home)
    cx = connect(home)
    try:
        if status:
            rows = cx.execute(
                "SELECT * FROM campaigns WHERE status = ? ORDER BY id",
                (status,)).fetchall()
        else:
            rows = cx.execute(
                "SELECT * FROM campaigns ORDER BY id").fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        cx.close()


# ----------------------------------------------------------------- schedule ---

def schedule_add(home, account_label, action_type, run_at, payload=None,
                 recurrence=""):
    init_db(home)
    cx = connect(home)
    try:
        cur = cx.execute(
            "INSERT INTO schedule (account_label, action_type, payload_json,"
            " run_at, recurrence, status)"
            " VALUES (?, ?, ?, ?, ?, 'pending')",
            (account_label, action_type, json.dumps(payload or {}), run_at,
             recurrence))
        sid = cur.lastrowid
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return sid


def schedule_list(home, status=None):
    init_db(home)
    cx = connect(home)
    try:
        if status:
            rows = cx.execute(
                "SELECT * FROM schedule WHERE status = ? ORDER BY run_at",
                (status,)).fetchall()
        else:
            rows = cx.execute(
                "SELECT * FROM schedule ORDER BY run_at").fetchall()
        out = []
        for r in rows:
            d = _row_to_dict(r)
            d["payload"] = json.loads(d.pop("payload_json") or "{}")
            out.append(d)
        return out
    finally:
        cx.close()


def schedule_set_status(home, sid, status):
    init_db(home)
    cx = connect(home)
    try:
        cx.execute("UPDATE schedule SET status = ? WHERE id = ?",
                   (status, sid))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)


# ------------------------------------------------------------------ content ---

def content_add(home, account_label, kind, title, file_path="", caption="",
                campaign_id=None, status="draft"):
    init_db(home)
    cx = connect(home)
    try:
        cur = cx.execute(
            "INSERT INTO content (account_label, campaign_id, kind, title,"
            " file_path, caption, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (account_label, campaign_id, kind, title, file_path, caption,
             status))
        cid = cur.lastrowid
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return cid


def content_list(home, account_label=None):
    init_db(home)
    cx = connect(home)
    try:
        if account_label:
            rows = cx.execute(
                "SELECT * FROM content WHERE account_label = ? ORDER BY id",
                (account_label,)).fetchall()
        else:
            rows = cx.execute("SELECT * FROM content ORDER BY id").fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        cx.close()


def content_set(home, cid, **fields):
    allowed = {"status", "posted_at", "platform_post_id", "caption", "title",
               "file_path", "campaign_id"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    init_db(home)
    cx = connect(home)
    try:
        cx.execute(
            "UPDATE content SET {} WHERE id = ?".format(
                ", ".join(f"{k} = ?" for k in updates)),
            (*updates.values(), cid))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)


# --------------------------------------------------------------- performance ---

def performance_log(home, content_id, platform, metric, value):
    init_db(home)
    cx = connect(home)
    try:
        cx.execute(
            "INSERT INTO performance (content_id, platform, metric, value,"
            " sampled_at) VALUES (?, ?, ?, ?, ?)",
            (content_id, platform, metric, value, utcnow()))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)


def performance_for(home, content_id):
    init_db(home)
    cx = connect(home)
    try:
        return [_row_to_dict(r) for r in cx.execute(
            "SELECT * FROM performance WHERE content_id = ?"
            " ORDER BY sampled_at", (content_id,)).fetchall()]
    finally:
        cx.close()


# ----------------------------------------------------------------- decisions ---

def log_decision(home, made_by, summary, rationale=""):
    init_db(home)
    cx = connect(home)
    try:
        cur = cx.execute(
            "INSERT INTO decisions (made_by, summary, rationale, created_at)"
            " VALUES (?, ?, ?, ?)", (made_by, summary, rationale, utcnow()))
        did = cur.lastrowid
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return did


def list_decisions(home, limit=50):
    init_db(home)
    cx = connect(home)
    try:
        return [_row_to_dict(r) for r in cx.execute(
            "SELECT * FROM decisions ORDER BY id DESC LIMIT ?",
            (limit,)).fetchall()]
    finally:
        cx.close()


# ---------------------------------------------------------------------- sops ---

def sop_add(home, title, body_md):
    init_db(home)
    cx = connect(home)
    try:
        row = cx.execute(
            "SELECT MAX(version) AS v FROM sops WHERE title = ?",
            (title,)).fetchone()
        version = (row["v"] or 0) + 1
        cur = cx.execute(
            "INSERT INTO sops (title, body_md, version, updated_at)"
            " VALUES (?, ?, ?, ?)", (title, body_md, version, utcnow()))
        sid = cur.lastrowid
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return sid, version


def sop_list(home):
    init_db(home)
    cx = connect(home)
    try:
        return [_row_to_dict(r) for r in cx.execute(
            "SELECT id, title, version, updated_at FROM sops"
            " ORDER BY title, version")]
    finally:
        cx.close()


def sop_get(home, sid):
    init_db(home)
    cx = connect(home)
    try:
        return _row_to_dict(cx.execute(
            "SELECT * FROM sops WHERE id = ?", (sid,)).fetchone())
    finally:
        cx.close()


# ----------------------------------------------------------------- relations ---

def parse_entity(ref):
    """Parse 'type:id' into (type, id)."""
    if ":" not in ref:
        raise ValueError(f"entity ref must look like 'type:id', got {ref!r}")
    etype, eid = ref.split(":", 1)
    etype, eid = etype.strip().lower(), eid.strip()
    if not etype or not eid:
        raise ValueError(f"bad entity ref {ref!r}")
    return etype, eid


def relate(home, subject_ref, predicate, object_ref, meta=None):
    """Add an edge to the relationship graph (idempotent)."""
    stype, sid = parse_entity(subject_ref)
    otype, oid = parse_entity(object_ref)
    predicate = predicate.strip().lower().replace(" ", "_")
    if not predicate:
        raise ValueError("predicate is required")
    init_db(home)
    cx = connect(home)
    try:
        cx.execute(
            "INSERT INTO relations (subject_type, subject_id, predicate,"
            " object_type, object_id, meta_json, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(subject_type, subject_id, predicate, object_type,"
            " object_id) DO UPDATE SET meta_json=excluded.meta_json",
            (stype, sid, predicate, otype, oid, json.dumps(meta or {}),
             utcnow()))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return {"subject": subject_ref, "predicate": predicate,
            "object": object_ref}


def graph(home, entity_ref, depth=1):
    """Return edges touching an entity (both directions), up to depth."""
    etype, eid = parse_entity(entity_ref)
    init_db(home)
    cx = connect(home)
    try:
        rows = cx.execute(
            "SELECT subject_type, subject_id, predicate, object_type,"
            " object_id, meta_json, created_at FROM relations"
            " WHERE (subject_type = ? AND subject_id = ?)"
            " OR (object_type = ? AND object_id = ?)"
            " ORDER BY created_at",
            (etype, eid, etype, eid)).fetchall()
    finally:
        cx.close()
    edges = []
    for r in rows:
        edges.append({
            "subject": f"{r['subject_type']}:{r['subject_id']}",
            "predicate": r["predicate"],
            "object": f"{r['object_type']}:{r['object_id']}",
            "meta": json.loads(r["meta_json"] or "{}"),
        })
    return edges


# ------------------------------------------------------------- read-only SQL ---

def query_select(home, sql):
    """Run a read-only SELECT. Anything else is refused."""
    stripped = sql.strip()
    if ";" in stripped:
        raise ValueError("only a single SELECT statement is allowed")
    first = stripped.split(None, 1)[0].upper() if stripped else ""
    if first != "SELECT":
        raise ValueError("only SELECT queries are allowed")
    init_db(home)
    cx = connect(home)
    try:
        # Defense in depth: read-only connection posture.
        cx.execute("PRAGMA query_only = ON")
        cur = cx.execute(stripped)
        cols = [d[0] for d in cur.description] if cur.description else []
        return cols, [dict(r) for r in cur.fetchall()]
    finally:
        cx.close()


def table_hashes(home):
    """Stable per-table content hashes (for incremental backups)."""
    init_db(home)
    cx = connect(home)
    try:
        out = {}
        for table in HASHED_TABLES:
            h = hashlib.sha256()
            n = 0
            for row in cx.execute(f"SELECT * FROM {table} ORDER BY rowid"):
                h.update(repr(tuple(row)).encode("utf-8", "replace"))
                n += 1
            out[table] = {"sha256": h.hexdigest(), "rows": n}
        return out
    finally:
        cx.close()


# ------------------------------------------------------------ conversations ---

CONVO_ROLES = ("user", "agent", "system")


def convo_log(home, role, text, account_label="", mission_id=None,
              kind="chat"):
    """Log one agent<->user turn worth remembering."""
    if role not in CONVO_ROLES:
        raise ValueError(f"bad role {role!r}")
    text = (text or "").strip()
    if not text:
        raise ValueError("conversation text is required")
    init_db(home)
    cx = connect(home)
    try:
        cur = cx.execute(
            "INSERT INTO conversations (ts, role, account_label, mission_id,"
            " kind, text) VALUES (?, ?, ?, ?, ?, ?)",
            (utcnow(), role, account_label, mission_id, kind,
             text[:4000]))
        cid = cur.lastrowid
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return cid


def convo_list(home, limit=50, account_label=None, mission_id=None):
    init_db(home)
    cx = connect(home)
    try:
        q = "SELECT * FROM conversations"
        clauses, params = [], []
        if account_label is not None:
            clauses.append("account_label = ?")
            params.append(account_label)
        if mission_id is not None:
            clauses.append("mission_id = ?")
            params.append(mission_id)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = cx.execute(q, params).fetchall()
        return [_row_to_dict(r) for r in reversed(rows)]
    finally:
        cx.close()


# --------------------------------------------------------- browser sessions ---

SESSION_STATUSES = ("new", "login_pending", "active", "challenge",
                    "paused", "expired")


def session_register(home, account_label, profile_dir, platform,
                     identity_id=""):
    """Register (or refresh) a host-browser session in memory.

    Host-browser model: the repo never drives a browser itself. When the
    external agent claims/fulfills an execution ticket in its own live browser,
    the claim is recorded here (which host agent + live session). The
    ``profile_dir`` argument is vestigial (kept for schema stability);
    host session ids are recorded via ``hands.tickets``.
    """
    init_db(home)
    cx = connect(home)
    try:
        cx.execute(
            "INSERT INTO browser_sessions (account_label, identity_id,"
            " profile_dir, platform, status, updated_at)"
            " VALUES (?, ?, ?, ?, 'new', ?)"
            " ON CONFLICT(account_label) DO UPDATE SET"
            " identity_id=excluded.identity_id,"
            " profile_dir=excluded.profile_dir,"
            " platform=excluded.platform, updated_at=excluded.updated_at",
            (account_label, identity_id, profile_dir, platform, utcnow()))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return session_get(home, account_label)


def session_set_status(home, account_label, status, challenge=None):
    if status not in SESSION_STATUSES:
        raise ValueError(f"bad session status {status!r}")
    init_db(home)
    cx = connect(home)
    try:
        cx.execute(
            "UPDATE browser_sessions SET status = ?, challenge = ?,"
            " updated_at = ? WHERE account_label = ?",
            (status, challenge, utcnow(), account_label))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return session_get(home, account_label)


def session_health(home, account_label, ok=True, note=""):
    """Record a session health check (ok=True/False)."""
    init_db(home)
    cx = connect(home)
    try:
        cx.execute(
            "UPDATE browser_sessions SET last_health_check = ?,"
            " status = CASE WHEN ? THEN status ELSE 'expired' END,"
            " updated_at = ? WHERE account_label = ?",
            (utcnow() + (" ok" if ok else f" FAIL: {note}"),
             1 if ok else 0, utcnow(), account_label))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return session_get(home, account_label)


def session_get(home, account_label):
    init_db(home)
    cx = connect(home)
    try:
        return _row_to_dict(cx.execute(
            "SELECT * FROM browser_sessions WHERE account_label = ?",
            (account_label,)).fetchone())
    finally:
        cx.close()


def session_list(home, status=None):
    init_db(home)
    cx = connect(home)
    try:
        if status:
            rows = cx.execute(
                "SELECT * FROM browser_sessions WHERE status = ?"
                " ORDER BY account_label", (status,)).fetchall()
        else:
            rows = cx.execute(
                "SELECT * FROM browser_sessions ORDER BY account_label"
            ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        cx.close()


# ----------------------------------------------------------------- missions ---

MISSION_STATUSES = ("pending", "active", "paused", "held", "completed",
                    "failed", "cancelled")


def mission_create(home, name, mission_type="custom", account_label="",
                   spec=None):
    """Create a mission record. Survives restarts; the resume engine
    picks up pending/active missions after a crash."""
    name = (name or "").strip()
    if not name:
        raise ValueError("mission name is required")
    init_db(home)
    cx = connect(home)
    try:
        now = utcnow()
        cx.execute(
            "INSERT INTO missions (name, mission_type, account_label,"
            " status, spec_json, created_at, updated_at)"
            " VALUES (?, ?, ?, 'pending', ?, ?, ?)"
            " ON CONFLICT(name) DO NOTHING",
            (name, mission_type, account_label, json.dumps(spec or {}),
             now, now))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return mission_get(home, name)


def mission_set_status(home, name, status, result=None):
    if status not in MISSION_STATUSES:
        raise ValueError(f"bad mission status {status!r}")
    init_db(home)
    cx = connect(home)
    try:
        if result is not None:
            cx.execute(
                "UPDATE missions SET status = ?, result_json = ?,"
                " updated_at = ? WHERE name = ?",
                (status, json.dumps(result), utcnow(), name))
        else:
            cx.execute(
                "UPDATE missions SET status = ?, updated_at = ?"
                " WHERE name = ?",
                (status, utcnow(), name))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return mission_get(home, name)


def mission_get(home, name):
    init_db(home)
    cx = connect(home)
    try:
        row = cx.execute(
            "SELECT * FROM missions WHERE name = ?", (name,)).fetchone()
        d = _row_to_dict(row)
        if d is None:
            return None
        d["spec"] = json.loads(d.pop("spec_json") or "{}")
        d["result"] = json.loads(d.pop("result_json") or "{}")
        return d
    finally:
        cx.close()


def mission_list(home, status=None):
    init_db(home)
    cx = connect(home)
    try:
        if status:
            rows = cx.execute(
                "SELECT * FROM missions WHERE status = ? ORDER BY id",
                (status,)).fetchall()
        else:
            rows = cx.execute(
                "SELECT * FROM missions ORDER BY id").fetchall()
        out = []
        for r in rows:
            d = _row_to_dict(r)
            d["spec"] = json.loads(d.pop("spec_json") or "{}")
            d["result"] = json.loads(d.pop("result_json") or "{}")
            out.append(d)
        return out
    finally:
        cx.close()


def mission_pending(home):
    """Missions the resume engine must pick back up."""
    out = []
    for status in ("pending", "active", "paused", "held"):
        out.extend(mission_list(home, status=status))
    return out


# ------------------------------------------------------------ actions ledger ---

def ledger_record(home, idem_key, action_type, target="", payload=None,
                  status="completed", mission_id=None, result=""):
    """Record a completed (or failed) action in the permanent ledger.

    idem_key is UNIQUE: the ledger is the second line of defense (after
    the journal) against duplicating platform actions after a crash."""
    if not idem_key:
        raise ValueError("idem_key is required")
    if status not in ("completed", "failed"):
        raise ValueError(f"bad ledger status {status!r}")
    init_db(home)
    cx = connect(home)
    try:
        now = utcnow()
        cx.execute(
            "INSERT INTO actions_ledger (idem_key, action_type, target,"
            " payload_json, status, mission_id, created_at, completed_at,"
            " result) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(idem_key) DO UPDATE SET"
            " status=excluded.status, completed_at=excluded.completed_at,"
            " result=excluded.result",
            (idem_key, action_type, target, json.dumps(payload or {}),
             status, mission_id, now, now, str(result)[:2000]))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return ledger_get(home, idem_key)


def ledger_get(home, idem_key):
    init_db(home)
    cx = connect(home)
    try:
        row = cx.execute(
            "SELECT * FROM actions_ledger WHERE idem_key = ?",
            (idem_key,)).fetchone()
        d = _row_to_dict(row)
        if d is None:
            return None
        d["payload"] = json.loads(d.pop("payload_json") or "{}")
        return d
    finally:
        cx.close()


def ledger_completed_keys(home):
    """All idempotency keys already completed — for duplicate checks."""
    init_db(home)
    cx = connect(home)
    try:
        return {r["idem_key"] for r in cx.execute(
            "SELECT idem_key FROM actions_ledger"
            " WHERE status = 'completed'").fetchall()}
    finally:
        cx.close()


def ledger_list(home, limit=100, status=None):
    init_db(home)
    cx = connect(home)
    try:
        if status:
            rows = cx.execute(
                "SELECT * FROM actions_ledger WHERE status = ?"
                " ORDER BY id DESC LIMIT ?", (status, limit)).fetchall()
        else:
            rows = cx.execute(
                "SELECT * FROM actions_ledger ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall()
        out = []
        for r in rows:
            d = _row_to_dict(r)
            d["payload"] = json.loads(d.pop("payload_json") or "{}")
            out.append(d)
        return out
    finally:
        cx.close()


# ------------------------------------------------------------- scheduler ---

SCHED_KINDS = ("once", "interval", "daily")
SCHED_STATUSES = ("enabled", "disabled", "paused")


def sched_add(home, name, kind, spec="", payload=None):
    """Register a scheduler job. ``kind``: once (spec=ISO run_at),
    interval (spec=seconds), daily (spec=HH:MM)."""
    name = (name or "").strip()
    if not name:
        raise ValueError("job name is required")
    if kind not in SCHED_KINDS:
        raise ValueError(f"bad scheduler kind {kind!r}")
    init_db(home)
    cx = connect(home)
    try:
        cx.execute(
            "INSERT INTO scheduler_jobs (name, kind, spec, payload_json,"
            " status, next_run, created_at)"
            " VALUES (?, ?, ?, ?, 'enabled', ?, ?)"
            " ON CONFLICT(name) DO NOTHING",
            (name, kind, spec, json.dumps(payload or {}),
             _initial_next_run(kind, spec), utcnow()))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return sched_get(home, name)


def _initial_next_run(kind, spec):
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    try:
        if kind == "once":
            return spec  # ISO timestamp supplied by caller
        if kind == "interval":
            secs = int(spec)
            return (now + timedelta(seconds=secs)).isoformat(
                timespec="seconds")
        if kind == "daily":
            hh, mm = spec.split(":")[:2]
            nxt = now.replace(hour=int(hh), minute=int(mm), second=0,
                              microsecond=0)
            if nxt <= now:
                nxt = nxt + timedelta(days=1)
            return nxt.isoformat(timespec="seconds")
    except (ValueError, IndexError):
        pass
    return now.isoformat(timespec="seconds")


def sched_get(home, name):
    init_db(home)
    cx = connect(home)
    try:
        row = cx.execute(
            "SELECT * FROM scheduler_jobs WHERE name = ?", (name,)
        ).fetchone()
        d = _row_to_dict(row)
        if d is None:
            return None
        d["payload"] = json.loads(d.pop("payload_json") or "{}")
        return d
    finally:
        cx.close()


def sched_list(home, status=None):
    init_db(home)
    cx = connect(home)
    try:
        if status:
            rows = cx.execute(
                "SELECT * FROM scheduler_jobs WHERE status = ?"
                " ORDER BY next_run", (status,)).fetchall()
        else:
            rows = cx.execute(
                "SELECT * FROM scheduler_jobs ORDER BY next_run"
            ).fetchall()
        out = []
        for r in rows:
            d = _row_to_dict(r)
            d["payload"] = json.loads(d.pop("payload_json") or "{}")
            out.append(d)
        return out
    finally:
        cx.close()


def sched_set(home, name, status=None, next_run=None):
    """Enable/disable/pause a job or override its next run."""
    if status is not None and status not in SCHED_STATUSES:
        raise ValueError(f"bad scheduler status {status!r}")
    init_db(home)
    cx = connect(home)
    try:
        if status is not None:
            cx.execute("UPDATE scheduler_jobs SET status = ? WHERE name = ?",
                       (status, name))
        if next_run is not None:
            cx.execute(
                "UPDATE scheduler_jobs SET next_run = ? WHERE name = ?",
                (next_run, name))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return sched_get(home, name)


def sched_mark_ran(home, name, ok=True):
    """Record a run; advance next_run for interval/daily jobs."""
    job = sched_get(home, name)
    if job is None:
        raise KeyError(f"unknown scheduler job {name!r}")
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    nxt = None
    if ok and job["kind"] == "interval":
        try:
            nxt = (now + timedelta(seconds=int(job["spec"]))).isoformat(
                timespec="seconds")
        except ValueError:
            nxt = None
    elif ok and job["kind"] == "daily":
        nxt = _initial_next_run("daily", job["spec"])
    init_db(home)
    cx = connect(home)
    try:
        cx.execute(
            "UPDATE scheduler_jobs SET last_run = ?, next_run = ?,"
            " run_count = run_count + 1 WHERE name = ?",
            (now.isoformat(timespec="seconds"), nxt, name))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return sched_get(home, name)


def sched_due(home, now_iso=None):
    """Jobs that are enabled and due at ``now_iso`` (default: now)."""
    now_iso = now_iso or utcnow()
    return [j for j in sched_list(home, status="enabled")
            if j.get("next_run") and j["next_run"] <= now_iso]


# --------------------------------------------------------------- analytics ---

def analytics_log(home, platform, metric, value, account_label="",
                  period=""):
    init_db(home)
    cx = connect(home)
    try:
        cx.execute(
            "INSERT INTO analytics (platform, account_label, metric, value,"
            " period, sampled_at) VALUES (?, ?, ?, ?, ?, ?)",
            (platform, account_label, metric, float(value), period,
             utcnow()))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)


def analytics_summary(home, platform=None, account_label=None):
    """Latest value per (platform, account, metric, period)."""
    init_db(home)
    cx = connect(home)
    try:
        q = ("SELECT platform, account_label, metric, period,"
             " MAX(sampled_at) AS sampled_at FROM analytics")
        clauses, params = [], []
        if platform is not None:
            clauses.append("platform = ?")
            params.append(platform)
        if account_label is not None:
            clauses.append("account_label = ?")
            params.append(account_label)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " GROUP BY platform, account_label, metric, period"
        latest = cx.execute(q, params).fetchall()
        out = []
        for r in latest:
            row = cx.execute(
                "SELECT value, sampled_at FROM analytics"
                " WHERE platform = ? AND account_label = ? AND metric = ?"
                " AND period = ? ORDER BY sampled_at DESC, id DESC LIMIT 1",
                (r["platform"], r["account_label"], r["metric"],
                 r["period"])).fetchone()
            out.append({"platform": r["platform"],
                        "account_label": r["account_label"],
                        "metric": r["metric"], "period": r["period"],
                        "value": row["value"],
                        "sampled_at": row["sampled_at"]})
        return sorted(out, key=lambda d: (d["platform"], d["metric"]))
    finally:
        cx.close()


# ---------------------------------------------------- brand voice (deepened) ---

def _voice_json_columns(home, account_label):
    cx = connect(home)
    try:
        row = cx.execute(
            "SELECT examples_json, style_rules_json, last_trained"
            " FROM brand_voice WHERE account_label = ?",
            (account_label,)).fetchone()
        if row is None:
            return {"examples": [], "style_rules": [], "last_trained": None}
        return {
            "examples": json.loads(row["examples_json"] or "[]"),
            "style_rules": json.loads(row["style_rules_json"] or "[]"),
            "last_trained": row["last_trained"],
        }
    finally:
        cx.close()


def voice_learn_example(home, account_label, example_text, kind="post"):
    """Teach the voice with a real example of the owner's writing."""
    example_text = (example_text or "").strip()
    if not example_text:
        raise ValueError("example text is required")
    init_db(home)
    cols = _voice_json_columns(home, account_label)
    examples = cols["examples"]
    entry = {"ts": utcnow(), "kind": kind, "text": example_text[:2000]}
    if entry["text"] not in [e.get("text") for e in examples]:
        examples.append(entry)
    examples = examples[-100:]  # keep the freshest 100
    cx = connect(home)
    try:
        cx.execute(
            "INSERT INTO brand_voice (account_label, updated_at,"
            " examples_json, last_trained)"
            " VALUES (?, ?, ?, ?)"
            " ON CONFLICT(account_label) DO UPDATE SET"
            " examples_json=excluded.examples_json,"
            " last_trained=excluded.last_trained,"
            " updated_at=excluded.updated_at",
            (account_label, utcnow(), json.dumps(examples), utcnow()))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return voice_profile(home, account_label)


def voice_learn_rule(home, account_label, rule):
    """Teach the voice one explicit style rule ("never start with 'hey guys'")."""
    rule = (rule or "").strip()
    if not rule:
        raise ValueError("rule is required")
    init_db(home)
    cols = _voice_json_columns(home, account_label)
    rules = cols["style_rules"]
    entry = {"ts": utcnow(), "rule": rule}
    if rule not in [e.get("rule") for e in rules]:
        rules.append(entry)
    rules = rules[-200:]
    cx = connect(home)
    try:
        cx.execute(
            "INSERT INTO brand_voice (account_label, updated_at,"
            " style_rules_json, last_trained)"
            " VALUES (?, ?, ?, ?)"
            " ON CONFLICT(account_label) DO UPDATE SET"
            " style_rules_json=excluded.style_rules_json,"
            " last_trained=excluded.last_trained,"
            " updated_at=excluded.updated_at",
            (account_label, utcnow(), json.dumps(rules), utcnow()))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return voice_profile(home, account_label)


def voice_profile(home, account_label):
    """Full decoded brand voice: tone, bans, dos/donts, examples, rules."""
    base = get_brand_voice(home, account_label) or {}
    cols = _voice_json_columns(home, account_label)
    return {
        "account_label": account_label,
        "tone_profile": base.get("tone_profile", ""),
        "banned_terms": json.loads(base.get("banned_terms_json") or "[]"),
        "dos": json.loads(base.get("dos_json") or "[]"),
        "donts": json.loads(base.get("donts_json") or "[]"),
        "examples": cols["examples"],
        "style_rules": cols["style_rules"],
        "last_trained": cols["last_trained"],
        "updated_at": base.get("updated_at"),
    }


# ------------------------------------------------------- watcher checkpoints ---

def checkpoint_save(home, watcher_id, platform, cursor, watcher_type="",
                    account_label=""):
    """Save a watcher checkpoint (last poll cursor) into the shared DB.

    The cursor is a dict like {"seen_ids": [...], "last_poll": iso,
    "polls": n, "events_found": n}. This is the authoritative resume
    state: the Watcher Engine replays these after a restart so every
    platform's watchers continue exactly where they stopped.
    """
    if not watcher_id:
        raise ValueError("watcher_id is required")
    init_db(home)
    cx = connect(home)
    try:
        cx.execute(
            "INSERT INTO watcher_checkpoints (watcher_id, platform,"
            " watcher_type, account_label, cursor_json, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(watcher_id) DO UPDATE SET platform=excluded.platform,"
            " watcher_type=excluded.watcher_type,"
            " account_label=excluded.account_label,"
            " cursor_json=excluded.cursor_json,"
            " updated_at=excluded.updated_at",
            (watcher_id, platform, watcher_type, account_label,
             json.dumps(dict(cursor or {})), utcnow()))
        cx.commit()
    finally:
        cx.close()
    _after_write(home)
    return checkpoint_get(home, watcher_id)


def checkpoint_get(home, watcher_id):
    """Return a decoded checkpoint dict, or None if the watcher never ran."""
    init_db(home)
    cx = connect(home)
    try:
        row = _row_to_dict(cx.execute(
            "SELECT * FROM watcher_checkpoints WHERE watcher_id = ?",
            (watcher_id,)).fetchone())
    finally:
        cx.close()
    if not row:
        return None
    try:
        cursor = json.loads(row.get("cursor_json") or "{}")
    except ValueError:
        cursor = {}
    row["cursor"] = cursor
    return row


def checkpoint_list(home, platform=None):
    """All checkpoints, optionally filtered to one platform."""
    init_db(home)
    cx = connect(home)
    try:
        if platform:
            rows = cx.execute(
                "SELECT * FROM watcher_checkpoints WHERE platform = ?"
                " ORDER BY watcher_id", (platform,)).fetchall()
        else:
            rows = cx.execute(
                "SELECT * FROM watcher_checkpoints ORDER BY platform,"
                " watcher_id").fetchall()
    finally:
        cx.close()
    out = []
    for r in rows:
        d = _row_to_dict(r)
        try:
            d["cursor"] = json.loads(d.get("cursor_json") or "{}")
        except ValueError:
            d["cursor"] = {}
        out.append(d)
    return out


def checkpoint_clear(home, watcher_id):
    """Remove a checkpoint (watcher deleted/reset)."""
    init_db(home)
    cx = connect(home)
    try:
        cx.execute("DELETE FROM watcher_checkpoints WHERE watcher_id = ?",
                   (watcher_id,))
        cx.commit()
    finally:
        cx.close()


# ------------------------------------------------------- platform memory view ---

class PlatformMemoryView:
    """Namespaced view into the SHARED memory DB for one platform.

    This is a VIEW, not a copy: there is exactly one memory.db per
    install, and every method below delegates to ``core.memory`` with
    the platform preset. ``platforms/<name>/memory/`` binds this to its
    platform — it must never contain its own database file.
    """

    def __init__(self, home, platform):
        self.home = home
        self.platform = platform

    # -- analytics scoped to this platform --
    def log_metric(self, metric, value, account_label="", period=""):
        return analytics_log(self.home, self.platform, metric, value,
                             account_label=account_label, period=period)

    def metrics(self, account_label=None):
        return analytics_summary(self.home, platform=self.platform,
                                 account_label=account_label)

    # -- conversations / missions scoped to this platform's accounts --
    def conversations(self, account_label=None, limit=50):
        return convo_list(self.home, limit=limit, account_label=account_label)

    def missions(self, status=None):
        ms = mission_list(self.home, status=status)
        return ms

    # -- watcher checkpoints for this platform (resume state) --
    def watcher_checkpoints(self):
        return checkpoint_list(self.home, platform=self.platform)

    # -- browser sessions for this platform's accounts --
    def sessions(self, account_label=None):
        ss = session_list(self.home)
        if account_label:
            ss = [s for s in ss if s["account_label"] == account_label]
        return ss
