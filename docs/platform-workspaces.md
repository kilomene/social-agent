# Platform workspaces

Every social platform gets its own source tree: `platforms/<platform>/`.
The design is generic — ANY platform (not just the seven we ship recipes
for) gets one via `social-agent workspace init --platform <name>`
(linkedin was added this way as the 7th platform).

## The tree

```
platforms/<name>/
  __init__.py        adapter spec (declarative, browser-only)
  terms.md / tos_rules.yaml
  watchers/          REGISTRATION manifest (which watchers + defaults)
  memory/            namespaced VIEW into the shared DB (no .db copy)
  browser_profile/   POINTER to the shared identity profile (no data)
  workspace/         shipped workspace template
```

## The two rules

1. **One shared browser profile per identity, all platforms.** Platform
   trees never own browser profiles. The profile lives at
   `identity/browser_profiles/<identity>/profile` and is registered in
   `identity/browser_profiles/<identity>.json` — one logged-in human
   browser, many tabs. The tree only records a *pointer* to it.
2. **Platform trees NEVER duplicate shared core.** Memory, the watcher
   engine, the browser engine, backup & recovery, the resume engine, the
   scheduler, the event bus, the video editor, audio engine, caption
   generator, analytics DB, and the human approval system exist exactly
   once (see `core/SHARED_CORE.md`). `tests/test_shared_core.py` fails
   the build if a shared-core module shows up under `platforms/`.

## Watcher lifecycle per platform

Platforms never implement watchers — they register them:

```python
from core.watcher_engine import WatcherEngine
from platforms.tiktok import watchers as tw

engine = WatcherEngine(home)            # shared engine, single instance
tw.register(engine, account="main")     # 14 watchers: tiktok:notification, ...
```

Registering the same platform twice is refused
(`DuplicateWatcherError`) — a watcher id is registered exactly once.

## What lives in a workspace

- `workspace.yaml` — platform name, identity + account labels, notes.
- `state/` — platform-specific runtime state. Survives restarts;
  covered by backups.
- `notes.md` — human-editable per-platform playbook notes (optional).

Watcher checkpoints (cursors) live in the shared memory DB
(`watcher_checkpoints` table), not in `state/` — a fresh VM resumes
watchers from memory without replaying or missing events. The JSON
sidecar under `<home>/watchers/<id>.json` is a legacy mirror only.

## What NEVER lives in a platform tree

Copies of shared-core modules, browser profile data, credentials, API
keys (there are no APIs — browser only), or cache files.
