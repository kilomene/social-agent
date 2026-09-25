"""Poll-based watcher framework.

Watchers are READ-ONLY monitors: they poll a source, detect new items, and
emit structured events. They never act (no posting, liking, commenting).
Actions are *proposed* inside events for a human/agent to approve elsewhere.

Offline operation: each watcher accepts an optional ``fixture`` — a JSON file
containing a list of items shaped like adapter output. Live operation feeds
items from a platform adapter (browser-driven); the framework does not care
where items come from, which keeps every watcher idempotent and testable.
"""

import json
import os
import time
from datetime import datetime, timezone

EVENTS_LOG = "events.jsonl"  # legacy constant; persistence now via core.event_bus
WATCHERS_DIR = "watchers"    # legacy JSON sidecar dir (kept for CLI readers)


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def as_list(value):
    """Normalize a list config that may arrive as a bare string via CLI --set."""
    if value is None:
        return []
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("["):
            try:
                import json
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except ValueError:
                pass
        # comma-separated or single bare value
        return [v.strip() for v in value.split(",") if v.strip()]
    return list(value)


class WatcherError(Exception):
    pass


class Watcher:
    """Base class. Subclasses set ``type``, ``description`` and ``schema``,
    and implement ``detect(items)``."""

    type = "base"
    description = "base watcher (do not use directly)"
    schema = {"required": [], "optional": {}}

    def __init__(self, watcher_id, platform, account, config, home, fixture=None):
        self.id = watcher_id
        self.platform = platform
        self.account = account
        self.config = dict(config or {})
        self.home = home
        self.fixture = fixture
        self.state_path = os.path.join(home, WATCHERS_DIR, f"{watcher_id}.json")
        self._state = {"seen_ids": [], "last_poll": None, "polls": 0, "events_found": 0}

    # ---- config ----
    def validate_config(self):
        errors = []
        req = self.schema.get("required", [])
        for key in req:
            if key not in self.config:
                errors.append(f"missing required config key: {key}")
        allowed = set(req) | set(self.schema.get("optional", {}).keys())
        for key in self.config:
            if key not in allowed:
                errors.append(f"unknown config key: {key}")
        return errors

    def effective_config(self):
        cfg = dict(self.schema.get("optional", {}))
        cfg.update(self.config)
        return cfg

    # ---- state (checkpoints) ----
    # The shared memory DB is the authoritative checkpoint store
    # (core.memory.watcher_checkpoints): after a crash/restart the Resume
    # Engine replays these so every platform's watchers continue exactly
    # where they stopped. The JSON sidecar under <home>/watchers/ is kept
    # as a legacy mirror for existing readers (CLI status, heartbeats).
    def _cursor(self):
        return {
            "seen_ids": list(self._state.get("seen_ids", [])),
            "last_poll": self._state.get("last_poll"),
            "polls": self._state.get("polls", 0),
            "events_found": self._state.get("events_found", 0),
        }

    def _save_checkpoint(self):
        try:
            from core import memory as mem_mod
            mem_mod.checkpoint_save(
                self.home, self.id, self.platform, self._cursor(),
                watcher_type=self.type, account_label=self.account)
        except Exception:
            # Checkpoints must never break a poll; the JSON sidecar
            # below still preserves the state locally.
            pass

    def load_state(self):
        loaded = False
        try:
            from core import memory as mem_mod
            cp = mem_mod.checkpoint_get(self.home, self.id)
            if cp and cp.get("cursor"):
                cur = cp["cursor"]
                self._state["seen_ids"] = list(cur.get("seen_ids", []))
                self._state["last_poll"] = cur.get("last_poll")
                self._state["polls"] = cur.get("polls", 0)
                self._state["events_found"] = cur.get("events_found", 0)
                loaded = True
        except Exception:
            loaded = False
        if not loaded and os.path.exists(self.state_path):
            with open(self.state_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self._state.update(data.get("state", {}))
        return self._state

    def save_state(self):
        self._save_checkpoint()
        record = {
            "id": self.id,
            "type": self.type,
            "platform": self.platform,
            "account": self.account,
            "config": self.config,
            "fixture": self.fixture,
            "state": self._state,
        }
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2)
        os.replace(tmp, self.state_path)

    # ---- polling ----
    def fetch(self):
        """Return raw items. Offline: from fixture file. Live: subclasses or
        adapters override this to pull from a browser-driven adapter."""
        if not self.fixture:
            return []
        with open(self.fixture, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            data = data.get("items", [])
        return data

    def detect(self, items):
        """Subclasses turn raw items into event dicts. Base: every item is an event."""
        return [
            self.make_event(
                item_id=str(it.get("id", i)),
                kind="item",
                summary=str(it.get("text") or it.get("title") or it.get("id")),
                data=it,
            )
            for i, it in enumerate(items)
        ]

    def make_event(self, item_id, kind, summary, data=None, proposed_action=None,
                   severity="info"):
        return {
            "id": f"{self.id}:{item_id}",
            "watcher": self.id,
            "watcher_type": self.type,
            "platform": self.platform,
            "account": self.account,
            "kind": kind,
            "severity": severity,
            "timestamp": utcnow(),
            "summary": summary,
            "data": data or {},
            "proposed_action": proposed_action,
        }

    def check(self):
        """One poll tick. Idempotent: re-running with the same items yields
        zero new events because seen ids are persisted."""
        errors = self.validate_config()
        if errors:
            raise WatcherError("; ".join(errors))
        self.load_state()
        seen = set(self._state.get("seen_ids", []))
        items = self.fetch()
        fresh = [it for it in items if str(it.get("id")) not in seen]
        events = self.detect(fresh)
        for it in fresh:
            seen.add(str(it.get("id")))
        self._state["seen_ids"] = sorted(seen)
        self._state["last_poll"] = utcnow()
        self._state["polls"] = self._state.get("polls", 0) + 1
        self._state["events_found"] = self._state.get("events_found", 0) + len(events)
        self.save_state()
        if events:
            from core import event_bus
            event_bus.publish(self.home, events)
        return events
