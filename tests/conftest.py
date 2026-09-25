"""Shared fixtures for social-agent tests."""

import json
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(REPO, "bin", "social-agent")
from core.watcher_engine import FIXTURES_DIR
FIXTURES = FIXTURES_DIR


@pytest.fixture
def home(tmp_path, monkeypatch):
    h = str(tmp_path / "home")
    monkeypatch.setenv("SOCIAL_AGENT_HOME", h)
    monkeypatch.delenv("SOCIAL_AGENT_POLICY", raising=False)
    return h


def cli(*args, home=None, policy=None, missions=None):
    env = dict(os.environ)
    if home:
        env["SOCIAL_AGENT_HOME"] = home
    if policy:
        env["SOCIAL_AGENT_POLICY"] = policy
    else:
        env.pop("SOCIAL_AGENT_POLICY", None)
    if missions:
        env["SOCIAL_AGENT_MISSIONS"] = missions
    else:
        env.pop("SOCIAL_AGENT_MISSIONS", None)
    return subprocess.run([sys.executable, CLI, *args],
                          capture_output=True, text=True, env=env)


def state(home_dir, name):
    p = os.path.join(home_dir, name)
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def write_policy(path, **overrides):
    """Write a minimal test policy.yaml with optional section overrides."""
    base = {
        "version": 1,
        "defaults": {"mode": "propose", "dry_run": True, "require_approval": True},
        "approvals": {"required_for": ["post", "like", "comment", "follow",
                                      "unfollow", "retweet", "dm"],
                      "approver": "user", "expiry_hours": 24},
        "quiet_hours": {"enabled": False, "start": "22:00", "end": "08:00",
                        "timezone": "local"},
        "rate_limits": {
            "default": {"actions_per_hour": 10, "actions_per_day": 50},
            "tiktok": {"actions_per_hour": 10, "actions_per_day": 40},
        },
        "watchers": {"poll_interval_seconds": 300, "max_events_per_poll": 50},
        "blocklists": {"keywords": [], "users": []},
        "interests": {
            "enabled": True,
            "topics": ["ai video", "sora"],
            "hashtags": ["aivideo"],
            "authors": [],
            "quality_signals": {"min_likes": 50, "min_comments": 5},
            "weights": {"topic": 2, "hashtag": 3, "author": 4,
                        "quality_signal": 1},
            "threshold": 5,
        },
        "engagement": {
            "likes_per_hour": 20,
            "likes_per_day": 100,
            "follows_per_day": 30,
            "like_author_cooldown_hours": 24,
            "min_seconds_between_likes": 60,
        },
        "prohibited": ["mass_follow_unfollow"],
    }
    for section, vals in overrides.items():
        if isinstance(vals, dict) and isinstance(base.get(section), dict):
            base[section].update(vals)
        else:
            base[section] = vals

    def dump(obj, indent=0):
        lines = []
        pad = "  " * indent
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{pad}{k}:")
                    lines.extend(dump(v, indent + 1))
                elif isinstance(v, str):
                    lines.append(f'{pad}{k}: "{v}"')
                elif v is True:
                    lines.append(f"{pad}{k}: true")
                elif v is False:
                    lines.append(f"{pad}{k}: false")
                else:
                    lines.append(f"{pad}{k}: {v}")
        elif isinstance(obj, list):
            for v in obj:
                if isinstance(v, dict):
                    lines.append(f"{pad}-")
                    lines.extend(dump(v, indent + 1))
                elif isinstance(v, str):
                    lines.append(f'{pad}- "{v}"')
                else:
                    lines.append(f"{pad}- {v}")
        return lines

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(dump(base)) + "\n")
    return path


def add_account(home_dir, platform="tiktok", username="tester", label="main"):
    r = cli("accounts", "add", "--platform", platform,
            "--username", username, "--label", label, home=home_dir)
    assert r.returncode == 0, r.stderr
