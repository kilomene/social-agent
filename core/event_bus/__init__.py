"""Event bus: shared-core event dispatch for watcher events.

Watchers are read-only pollers; when they find something they emit
structured events. This bus owns the two things that happen next:

  1. persistence — every event is appended to ``<home>/events.jsonl``
     (the audit trail every downstream consumer reads);
  2. dispatch — in-process handlers subscribed by kind prefix run on
     each event (the listener pipeline, analytics taps, test hooks).

Nothing here acts on a platform. Handlers may only observe, classify,
and *propose* — acting still requires the approval queue.
"""

import json
import os

EVENTS_LOG = "events.jsonl"

_handlers = {}  # kind-prefix -> [callable(home, event)]


def subscribe(kind_prefix, fn):
    """Run ``fn(home, event)`` for every event whose kind starts with
    ``kind_prefix``. Returns the handler (for unsubscribe)."""
    _handlers.setdefault(kind_prefix, []).append(fn)
    return fn


def unsubscribe(kind_prefix, fn):
    handlers = _handlers.get(kind_prefix, [])
    if fn in handlers:
        handlers.remove(fn)


def clear():
    """Remove all subscriptions (tests)."""
    _handlers.clear()


def dispatch(home, event):
    """Run matching handlers. A failing handler is reported, never fatal."""
    kind = str(event.get("kind", ""))
    for prefix, handlers in list(_handlers.items()):
        if kind.startswith(prefix):
            for fn in list(handlers):
                try:
                    fn(home, event)
                except Exception as exc:  # noqa: BLE001 — dispatch is best-effort
                    event.setdefault("dispatch_errors", []).append(
                        f"{getattr(fn, '__name__', 'handler')}: {exc}")


def publish(home, events):
    """Persist events and dispatch them. Returns the number published."""
    events = list(events or [])
    if events:
        path = os.path.join(home, EVENTS_LOG)
        os.makedirs(home, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            for ev in events:
                fh.write(json.dumps(ev) + "\n")
    for ev in events:
        dispatch(home, ev)
    return len(events)


def read_events(home, limit=1000):
    """Read back the persisted event log (newest last)."""
    path = os.path.join(home, EVENTS_LOG)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out[-limit:]
