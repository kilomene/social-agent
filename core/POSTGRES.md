# Postgres scale-up path

`core/memory.py` uses sqlite3 (stdlib) — zero dependencies, perfect for one
agent. If you outgrow SQLite (multiple writers, replication, >GBs of
performance samples), the schema ports 1:1 to Postgres.

## Connection

The Postgres path is **not** implemented in this repo (stdlib-only rule).
To adopt it:

1. Add a `db.py` adapter with the same function signatures as
   `core/memory.py`, backed by `psycopg`.
2. Read the DSN from the environment — **never from the repo**:
   `SOCIAL_AGENT_DATABASE_URL=postgresql://user@host/dbname`.
3. Keep `memory.db` as the offline fallback; sync on reconnect.

## Schema notes (SQLite -> Postgres)

- `INTEGER PRIMARY KEY AUTOINCREMENT` -> `GENERATED ALWAYS AS IDENTITY`
  (or `SERIAL`).
- `ON CONFLICT(label) DO UPDATE` works as-is in Postgres.
- `*_json TEXT` columns -> `JSONB` (queries on tags/notes get indexes).
- `relations` unique constraint ports directly; add a GIN index on
  `meta_json` if you filter on it.
- `PRAGMA query_only = ON` (used by `memory query`) -> open a transaction
  with `SET TRANSACTION READ ONLY`, or connect as a read-only role.
- Timestamps are ISO-8601 text here; use `TIMESTAMPTZ` there.

## What doesn't change

Table names, column names, the relationship-graph model, the incremental
backup design (pg_dump per table + hashes instead of file copy), and the
journal format all stay identical — only the storage driver changes.
