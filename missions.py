"""Missions: a defined area of work for autonomous operation.

A mission is a Markdown file `missions/<name>.md` with YAML front-matter:

    ---
    name: ai-video-growth
    platforms:
      - tiktok
      - instagram
    topics:
      - ai video
      - sora
    allowed_actions:
      - post
      - like
      - follow
      - comment
    limits:
      posts_per_day: 2
      likes_per_day: 50
      follows_per_day: 10
    ---
    # Mission: ai-video-growth
    Free-text brief: content pillars, tone, what success looks like...

The front-matter is parsed with policy/yaml_lite.py (block style only, no
flow syntax). Missions never grant: profile changes, DMs, or off-mission
platforms — those are hard-blocked by autonomy.check_scope().
"""

import os
import re

from policy import yaml_lite

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)

REQUIRED_KEYS = ["name", "platforms", "allowed_actions"]


def missions_dir():
    return os.environ.get("SOCIAL_AGENT_MISSIONS",
                           os.path.join(REPO_ROOT, "missions"))


def mission_path(name):
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", name)
    return os.path.join(missions_dir(), f"{safe}.md")


def parse_mission_file(path):
    """Parse a mission file -> (front_matter_dict, body_markdown). Raises ValueError."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = FRONT_MATTER_RE.match(text)
    if not m:
        raise ValueError(f"{path}: missing YAML front-matter (--- block)")
    try:
        meta = yaml_lite.loads(m.group(1))
    except Exception as e:
        raise ValueError(f"{path}: bad front-matter: {e}")
    if not isinstance(meta, dict):
        raise ValueError(f"{path}: front-matter must be a mapping")
    errors = [f"missing required key: {k}" for k in REQUIRED_KEYS if k not in meta]
    if errors:
        raise ValueError(f"{path}: " + "; ".join(errors))
    return meta, text[m.end():]


def validate_mission(meta):
    errors = []
    if not isinstance(meta.get("platforms"), list) or not meta["platforms"]:
        errors.append("platforms must be a non-empty list")
    if not isinstance(meta.get("allowed_actions"), list) or not meta["allowed_actions"]:
        errors.append("allowed_actions must be a non-empty list")
    for a in meta.get("allowed_actions", []):
        if a in ("dm", "profile"):
            errors.append(f"action {a!r} can never be mission-scoped (hard-blocked)")
    return errors


def list_missions():
    out = []
    d = missions_dir()
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".md"):
            continue
        try:
            meta, _ = parse_mission_file(os.path.join(d, fn))
            out.append(meta)
        except ValueError:
            continue
    return out


def get_mission(name):
    p = mission_path(name)
    if not os.path.exists(p):
        return None
    meta, _ = parse_mission_file(p)
    return meta


def create_mission(name, platforms, topics, allowed_actions, limits, brief=""):
    """Write missions/<name>.md. Returns the path."""
    meta_lines = [
        "---",
        f"name: {name}",
        "platforms:",
    ]
    meta_lines += [f"  - {p}" for p in platforms]
    meta_lines.append("topics:")
    meta_lines += [f"  - {t}" for t in topics]
    meta_lines.append("allowed_actions:")
    meta_lines += [f"  - {a}" for a in allowed_actions]
    meta_lines.append("limits:")
    for k, v in (limits or {}).items():
        meta_lines.append(f"  {k}: {v}")
    meta_lines.append("---")
    body = (brief or f"# Mission: {name}\n\nArea of work defined via CLI.\n").strip() + "\n"
    text = "\n".join(meta_lines) + "\n" + body
    # validate before writing
    meta = yaml_lite.loads("\n".join(meta_lines[1:-1]))
    errors = validate_mission(meta)
    if errors:
        raise ValueError("; ".join(errors))
    os.makedirs(missions_dir(), exist_ok=True)
    p = mission_path(name)
    if os.path.exists(p):
        raise ValueError(f"mission {name!r} already exists")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p
