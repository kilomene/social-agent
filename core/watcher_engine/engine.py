"""Watcher Engine: shared-core scheduling, lifecycle, event dispatch and
crash recovery for watchers.

Watchers are READ-ONLY monitors that poll a source and emit structured
events — they never act. Each platform REGISTERS its watchers with this
one shared engine (see platforms/<name>/watchers/); no watcher logic is
duplicated anywhere.

Lifecycle per watcher: register -> enable -> poll (tick) -> disable/stop.
Every poll writes a checkpoint (last poll cursor) into the shared memory
DB, so the Resume Engine can restore every platform's watchers exactly
where they stopped after a crash or VM restart.

Registration records live in <home>/watchers.json (the same file the
``watch`` CLI has always used), so CLI-created and platform-registered
watchers share one registry.
"""

import json
import os
import time

from .framework import Watcher, WatcherError, utcnow
from .watchers import REGISTRY

REGISTRY_PATH = "watchers.json"


class DuplicateWatcherError(WatcherError):
    """A watcher with this id is already registered."""


class UnknownWatcherTypeError(WatcherError):
    """No watcher class registered under this type name."""


class WatcherEngine:
    """One engine per install; platforms register, the engine runs."""

    def __init__(self, home, tos_check=None):
        self.home = home
        # tos_check(platform) -> None or raises. Injected so shared core
        # never hard-depends on the ToS layer.
        self.tos_check = tos_check
        self._registered = {}
        self._load()

    # ---- registry persistence ----
    def _path(self):
        return os.path.join(self.home, REGISTRY_PATH)

    def _load(self):
        if os.path.exists(self._path()):
            with open(self._path(), encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                self._registered.update(data)

    def _save(self):
        os.makedirs(self.home, exist_ok=True)
        tmp = self._path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._registered, fh, indent=2)
        os.replace(tmp, self._path())

    # ---- registration ----
    def register(self, watcher_id, watcher_type, platform, account,
                 config=None, fixture=None, enabled=True):
        """Register one watcher. A duplicate id is REFUSED (fail-closed)."""
        if watcher_type not in REGISTRY:
            raise UnknownWatcherTypeError(
                f"unknown watcher type {watcher_type!r}"
                f" (known: {', '.join(sorted(REGISTRY))})")
        if watcher_id in self._registered:
            raise DuplicateWatcherError(
                f"watcher {watcher_id!r} is already registered")
        cls = REGISTRY[watcher_type]
        probe = cls(watcher_id, platform, account, config or {},
                    self.home, fixture)
        errors = probe.validate_config()
        if errors:
            raise WatcherError("invalid config: " + "; ".join(errors))
        rec = {
            "id": watcher_id, "type": watcher_type, "platform": platform,
            "account": account, "config": dict(config or {}),
            "fixture": fixture, "enabled": bool(enabled),
            "started": utcnow(),
        }
        self._registered[watcher_id] = rec
        self._save()
        return rec

    def register_platform(self, platform, specs):
        """Register every watcher a platform declares.

        ``specs`` is a list of watcher types or (type, config) pairs —
        exactly what platforms/<name>/watchers/ declares. Duplicate
        registration of the same platform is refused per-watcher.
        """
        registered = []
        for spec in specs:
            if isinstance(spec, (tuple, list)):
                wtype, cfg = spec[0], (spec[1] if len(spec) > 1 else {})
            else:
                wtype, cfg = spec, {}
            wid = f"{platform}:{wtype}"
            registered.append(self.register(wid, wtype, platform,
                                            account="", config=cfg))
        return registered

    def unregister(self, watcher_id):
        if watcher_id not in self._registered:
            raise WatcherError(f"unknown watcher {watcher_id!r}")
        del self._registered[watcher_id]
        self._save()

    def enable(self, watcher_id):
        self._registered[self._require(watcher_id)]["enabled"] = True
        self._save()

    def disable(self, watcher_id):
        self._registered[self._require(watcher_id)]["enabled"] = False
        self._save()

    def _require(self, watcher_id):
        if watcher_id not in self._registered:
            raise WatcherError(f"unknown watcher {watcher_id!r}")
        return watcher_id

    def get(self, watcher_id):
        return self._registered.get(watcher_id)

    def list(self, platform=None, enabled_only=False):
        out = [r for r in self._registered.values()
               if (platform is None or r["platform"] == platform)
               and (not enabled_only or r.get("enabled"))]
        return sorted(out, key=lambda r: r["id"])

    def watchers_for_platform(self, platform):
        return self.list(platform=platform)

    def register_platform_package(self, package, account="",
                                    fixtures_dir=None):
        """Register from a ``platforms.<name>.watchers`` package.

        The package is pure data: ``PLATFORM``, ``WATCHERS`` (list of
        (type, defaults)), and ``FIXTURE_FILES`` (type -> fixture
        filename). All logic stays in the engine.
        """
        import sys as _sys
        from core.watcher_engine import FIXTURES_DIR as ENGINE_FIXTURES
        if isinstance(package, str):
            package = _sys.modules[package]
        fdir = fixtures_dir or ENGINE_FIXTURES
        filemap = getattr(package, "FIXTURE_FILES", {}) or {}
        fixtures = {}
        for wtype, fname in filemap.items():
            cand = os.path.join(fdir, fname)
            if os.path.exists(cand):
                fixtures[wtype] = cand
        return self.register_platform_manifest(
            package.PLATFORM, package.WATCHERS,
            account=account, fixtures=fixtures)

    # ---- platform manifests ----
    def register_platform_manifest(self, platform, watcher_specs, account="",
                                   fixtures=None):
        """Register every watcher a platform declares.

        ``watcher_specs`` is the platform's manifest: a list of
        ``(watcher_type, defaults)`` pairs (exactly what
        ``platforms/<name>/watchers/`` declares). ``fixtures`` optionally
        maps watcher type -> fixture file path (offline mode).
        """
        fixtures = fixtures or {}
        registered = []
        for spec in watcher_specs:
            if isinstance(spec, (tuple, list)):
                wtype, cfg = spec[0], dict(spec[1] if len(spec) > 1 else {})
            else:
                wtype, cfg = spec, {}
            wid = f"{platform}:{wtype}"
            registered.append(self.register(
                wid, wtype, platform, account=account, config=cfg,
                fixture=fixtures.get(wtype)))
        return registered

    # ---- polling ----
    def _instantiate(self, rec):
        cls = REGISTRY[rec["type"]]
        return cls(rec["id"], rec["platform"], rec["account"],
                   rec.get("config"), self.home, rec.get("fixture"))

    def poll(self, watcher_id):
        """One poll tick for one watcher. Checkpoints are written by the
        watcher itself; ToS is enforced before any poll."""
        rec = self._registered[self._require(watcher_id)]
        if not rec.get("enabled"):
            raise WatcherError(f"watcher {watcher_id} is disabled")
        if self.tos_check is not None:
            self.tos_check(rec["platform"])
        watcher = self._instantiate(rec)
        return watcher.check()

    def poll_platform(self, platform, only=None):
        """Poll every enabled watcher of one platform. Returns
        {watcher_id: events} (a refusal or error is recorded, not fatal)."""
        results = {}
        for rec in self.list(platform=platform, enabled_only=True):
            if only and rec["id"] not in only:
                continue
            try:
                results[rec["id"]] = self.poll(rec["id"])
            except Exception as exc:
                results[rec["id"]] = {"error": str(exc)}
        return results

    def poll_all(self, platforms=None, only=None):
        results = {}
        plats = platforms or sorted(
            {r["platform"] for r in self._registered.values()})
        for p in plats:
            results[p] = self.poll_platform(p, only=only)
        return results

    # ---- crash recovery ----
    def checkpoints(self, platform=None):
        """Watcher checkpoints from the shared memory DB (resume state)."""
        from core import memory as mem_mod
        return mem_mod.checkpoint_list(self.home, platform=platform)

    def resume_report(self, platform=None):
        """Where every watcher stopped: id -> last cursor summary.

        The Resume Engine replays this after a restart.
        """
        report = []
        for rec in self.list(platform=platform):
            cp = None
            try:
                from core import memory as mem_mod
                cp = mem_mod.checkpoint_get(self.home, rec["id"])
            except Exception:
                cp = None
            cursor = (cp or {}).get("cursor", {})
            report.append({
                "id": rec["id"], "type": rec["type"],
                "platform": rec["platform"],
                "enabled": rec.get("enabled", True),
                "last_poll": cursor.get("last_poll"),
                "polls": cursor.get("polls", 0),
                "events_found": cursor.get("events_found", 0),
                "seen": len(cursor.get("seen_ids", [])),
                "has_checkpoint": cp is not None,
            })
        return report
