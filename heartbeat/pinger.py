"""Stdlib heartbeat pinger: HTTP GET pings + local audit log."""

import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = "heartbeat.json"
MAX_HISTORY = 200


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _home():
    return os.environ.get("SOCIAL_AGENT_HOME", os.path.expanduser("~/.social-agent"))


class HeartbeatConfig:
    def __init__(self, data=None):
        d = data or {}
        self.enabled = d.get("enabled", True)
        self.base_url = (d.get("base_url") or "").rstrip("/")
        self.timeout = d.get("timeout_seconds", 10)
        sup = d.get("supervisor") or {}
        self.supervisor_enabled = sup.get("enabled", True)
        self.supervisor_interval = sup.get("interval_seconds", 10)
        self.supervisor_name = sup.get("name", "social-agent-supervisor")
        self.watcher_overrides = d.get("watchers") or {}

    def watcher_url(self, watcher_id):
        ov = self.watcher_overrides.get(watcher_id) or {}
        if ov.get("url"):
            return ov["url"].rstrip("/")
        return self.base_url

    def watcher_enabled(self, watcher_id):
        ov = self.watcher_overrides.get(watcher_id) or {}
        return ov.get("enabled", True)


def config_path():
    return os.environ.get("SOCIAL_AGENT_HEARTBEAT",
                          os.path.join(REPO_ROOT, "heartbeat.yaml"))


def load_config(path=None):
    from policy import yaml_lite
    p = path or config_path()
    data = {}
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            data = yaml_lite.loads(fh.read()) or {}
    return HeartbeatConfig(data)


def record_local(name, path, ok, detail=""):
    """Append a ping record to the local audit log. Always runs (even log-only)."""
    entry = {"timestamp": utcnow(), "name": name, "path": path,
             "ok": bool(ok), "detail": detail}
    lp = os.path.join(_home(), LOG_FILE)
    hist = []
    if os.path.exists(lp):
        try:
            with open(lp, encoding="utf-8") as fh:
                hist = json.load(fh)
        except (json.JSONDecodeError, OSError):
            hist = []
    hist.append(entry)
    hist = hist[-MAX_HISTORY:]
    os.makedirs(_home(), exist_ok=True)
    tmp = lp + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(hist, fh, indent=2)
    os.replace(tmp, lp)
    return entry


def ping(url, timeout=10, name="ping"):
    """GET <url>. Returns (ok, detail). Never raises."""
    if not url:
        record_local(name, "(log-only)", True, "no base_url configured")
        return True, "log-only (no base_url)"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "social-agent/heartbeat"})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ms = int((time.time() - t0) * 1000)
            ok = 200 <= resp.status < 300
            detail = f"HTTP {resp.status} in {ms}ms"
    except Exception as e:  # network is best-effort; the local log is the record
        ok, detail = False, f"{type(e).__name__}: {e}"
    record_local(name, url, ok, detail)
    return ok, detail


def ping_path(base_url, name, suffix="", timeout=10):
    """Ping <base_url>/<name>[/<suffix>]. Empty base -> log-only record."""
    path = f"{name}/{suffix}" if suffix else name
    if not base_url:
        record_local(name, path, True, "log-only (no base_url)")
        return True, "log-only (no base_url)"
    return ping(f"{base_url}/{path}", timeout=timeout, name=name)


def watch_run(config, name, fn, timeout=None):
    """Heartbeat `watch` semantics: ping start, run fn, ping success or /fail.

    Returns fn()'s result. On exception, pings <name>/fail and re-raises.
    When disabled or log-only, still records to the local audit log.
    """
    if not config.enabled or not config.watcher_enabled(name):
        return fn()
    base = config.watcher_url(name)
    tmo = timeout if timeout is not None else config.timeout
    ping_path(base, name, "start", timeout=tmo)
    try:
        result = fn()
    except Exception as e:
        ping_path(base, name, "fail", timeout=tmo)
        raise
    ping_path(base, name, "", timeout=tmo)
    return result


def recent_pings(limit=20, name=None):
    lp = os.path.join(_home(), LOG_FILE)
    if not os.path.exists(lp):
        return []
    with open(lp, encoding="utf-8") as fh:
        hist = json.load(fh)
    if name:
        hist = [h for h in hist if h.get("name") == name]
    return hist[-limit:]
