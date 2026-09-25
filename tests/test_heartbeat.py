"""Heartbeat module tests (stdlib only, log-only mode)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from heartbeat import pinger
from conftest import FIXTURES, add_account, cli


def test_load_config_defaults():
    cfg = pinger.load_config()
    assert cfg.enabled is True
    assert cfg.supervisor_interval == 10
    assert cfg.base_url == ""  # log-only by default


def test_ping_log_only(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIAL_AGENT_HOME", str(tmp_path))
    ok, detail = pinger.ping("", name="w1")
    assert ok and "log-only" in detail
    with open(tmp_path / "heartbeat.json") as fh:
        hist = json.load(fh)
    assert hist[-1]["name"] == "w1"


def test_watch_run_success_records_start_and_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIAL_AGENT_HOME", str(tmp_path))
    cfg = pinger.HeartbeatConfig({"base_url": ""})
    out = pinger.watch_run(cfg, "w-test", lambda: 42)
    assert out == 42
    with open(tmp_path / "heartbeat.json") as fh:
        hist = json.load(fh)
    paths = [h["path"] for h in hist if h["name"] == "w-test"]
    assert any(p.endswith("/start") for p in paths)
    assert any(p == "w-test" or p.endswith("/w-test") for p in paths)
    assert not any(p.endswith("/fail") for p in paths)


def test_watch_run_failure_records_fail(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIAL_AGENT_HOME", str(tmp_path))
    cfg = pinger.HeartbeatConfig({"base_url": ""})

    def boom():
        raise RuntimeError("kaput")

    try:
        pinger.watch_run(cfg, "w-bad", boom)
        assert False, "should have raised"
    except RuntimeError:
        pass
    with open(tmp_path / "heartbeat.json") as fh:
        hist = json.load(fh)
    paths = [h["path"] for h in hist if h["name"] == "w-bad"]
    assert any(p.endswith("/start") for p in paths)
    assert any(p.endswith("/fail") for p in paths)


def test_watch_run_emits_heartbeat_via_cli(home):
    add_account(home)
    fx = os.path.join(FIXTURES, "notifications.json")
    cli("watch", "start", "--type", "notification", "--platform", "tiktok",
        "--account", "main", "--fixture", fx, "--id", "hbw", home=home)
    r = cli("watch", "run", "hbw", home=home)
    assert r.returncode == 0
    with open(os.path.join(home, "heartbeat.json")) as fh:
        hist = json.load(fh)
    paths = [h["path"] for h in hist if h["name"] == "hbw"]
    assert any(p.endswith("/start") for p in paths)
    assert any(p.endswith("/fail") for p in paths) is False


def test_heartbeat_status_and_test_commands(home):
    r = cli("heartbeat", "status", home=home)
    assert r.returncode == 0 and "log-only" in r.stdout
    r = cli("heartbeat", "test", home=home)
    assert r.returncode == 0 and "log-only" in r.stdout
