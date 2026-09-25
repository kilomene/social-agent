# Shared core — single instance, used by EVERY platform

These services exist exactly once per installation. Every platform gets
its own source tree (`platforms/<name>/`), but the tree NEVER duplicates
shared core — it only holds platform-specific declarations:

```
platforms/<name>/
  __init__.py        adapter spec (declarative, no-API: hands handoff via execution tickets
                     fulfilled in the external agent's live browser)
  terms.md / tos_rules.yaml
  watchers/          REGISTRATION manifest (which watchers + defaults)
  memory/            namespaced VIEW into the shared DB (no .db copy)
  workspace/         shipped workspace template
```

The rule is enforced by `tests/test_shared_core.py`: any shared-core
module basename or package directory found under `platforms/<name>/`
fails the build. The top-level `watchers/` directory is deleted —
`import watchers` fails loudly; the engine lives in core.

| # | Service | Module | Notes |
|---|---------|--------|-------|
| 1 | Permanent memory | `core/memory.py` (+ `memory.db`) | the center of the system; journal is source of truth; `PlatformMemoryView` gives each platform a namespaced view |
| 2 | Watcher engine | `core/watcher_engine/` | scheduling, lifecycle, event dispatch, crash recovery; platforms REGISTER watchers, classes live here once |
| 3 | Hands handoff | execution tickets (`social-agent tickets` / `ticket show|claim|fulfill|cancel|fail`) | approval issues a ticket (issued → claimed → fulfilled, idempotent); the external agent fulfills it visibly in its own browser (`docs/HOST_BROWSER.md`); `identity/host_sessions/` records who performed each action — the repo drives no browser itself |
| 4 | Backup & recovery | `core/backup.py`, `core/remote.py` | dual-backup: local versioned + optional encrypted remote |
| 5 | Resume engine | `core/resume_engine/` | journal replay, missions, watcher checkpoints (`core/recovery.py` is a back-compat shim) |
| 6 | Scheduler | `core/scheduler/` | state in memory DB; survives restarts |
| 7 | Event bus | `core/event_bus/` | watcher event persistence + dispatch |
| 8 | Video editor | `editor/` | Kdenlive/ffmpeg worker |
| 9 | Audio engine | `audio/` | clipping, mixing, LUFS |
| 10 | Caption generator | `captions/` | platform-normed captions |
| 11 | Analytics database | `core/memory.py` (`analytics` table) | per-platform performance rollups |
| 12 | Human approval system | `approvals/` | unified queue; every proposal reviewed in one place |

Related singletons (not duplicated either): `platforms/tos.py` (ToS
enforcement), `ratelimit/` (central rate-limit controller), `crisis/`
(kill switch), `identity/` (identity store).

When adding a new platform:
1. create `platforms/<name>/` with `__init__.py` (ADAPTER spec),
   `terms.md` + `tos_rules.yaml`, and the three subdirs
   (`watchers/`, `memory/`, `workspace/`). Execution needs no recipe:
   approved actions become execution tickets fulfilled by the external
   agent in its own live browser (`docs/HOST_BROWSER.md`);
2. register the name in `platforms/base.py` (`SUPPORTED_PLATFORMS` +
   `get_adapter`);
3. declare its watchers in `platforms/<name>/watchers/__init__.py`.

Do NOT copy shared-core modules into the platform tree.
