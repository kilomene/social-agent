"""Persistent pipeline state: atomic full-snapshot writes + resume.

New store: <home>/video_pipeline/ — never the live loop stores
(queue.json, tickets.json, approvals/pending.json, actions.json,
render_queue.json, video_plans/). Resume = re-read persisted node
outputs, skip succeeded nodes, never restart from zero.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone

from . import definition as d

PIPELINE_DIR = "video_pipeline"
EPISODES_FILE = "episodes.json"
STATE_FILE = "state.json"
ASSETS_DIR = "assets"


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def pipeline_home(home):
    """Absolute path of the pipeline store for a SOCIAL_AGENT_HOME."""
    return os.path.join(os.path.abspath(home), PIPELINE_DIR)


def _atomic_write(path, payload):
    """Full-snapshot atomic write: temp file in same dir + os.replace."""
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp-",
                               suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# --- episode registry ---------------------------------------------------------
class EpisodeRegistry:
    """episodes.json: {episode_id: {title, dir, status, updated_at}}."""

    def __init__(self, home):
        self.home = pipeline_home(home)
        self.path = os.path.join(self.home, EPISODES_FILE)

    def load(self):
        return _read_json(self.path, {})

    def register(self, episode):
        reg = self.load()
        reg[episode["id"]] = {
            "title": episode.get("title", ""),
            "dir": episode["id"],
            "status": episode.get("status", "defined"),
            "updated_at": utcnow(),
        }
        _atomic_write(self.path, reg)

    def set_status(self, episode_id, status):
        reg = self.load()
        if episode_id not in reg:
            raise KeyError(f"unknown episode {episode_id!r}")
        reg[episode_id]["status"] = status
        reg[episode_id]["updated_at"] = utcnow()
        _atomic_write(self.path, reg)

    def get(self, episode_id):
        return self.load().get(episode_id)


# --- episode state ------------------------------------------------------------
class EpisodeState:
    """Per-episode dir: state.json + assets/. Full-snapshot atomic writes."""

    def __init__(self, home, episode_id):
        self.home = pipeline_home(home)
        self.episode_id = episode_id
        self.dir = os.path.join(self.home, episode_id)
        self.path = os.path.join(self.dir, STATE_FILE)
        self.assets_dir = os.path.join(self.dir, ASSETS_DIR)
        self._doc = None

    # -- lifecycle ---------------------------------------------------------
    def exists(self):
        return os.path.exists(self.path)

    def create(self, episode):
        if self.exists():
            raise ValueError(f"episode {self.episode_id!r} already exists")
        doc = dict(episode)
        doc["created_at"] = utcnow()
        doc["updated_at"] = utcnow()
        _atomic_write(self.path, doc)
        os.makedirs(os.path.join(self.assets_dir, "generated"), exist_ok=True)
        self._doc = doc
        EpisodeRegistry(self._home_root()).register(doc)
        return doc

    def _home_root(self):
        return os.path.dirname(self.home)

    def load(self):
        self._doc = _read_json(self.path, None)
        if self._doc is None:
            raise KeyError(f"no state for episode {self.episode_id!r}")
        return self._doc

    def doc(self):
        return self._doc if self._doc is not None else self.load()

    def save(self):
        doc = self.doc()
        doc["updated_at"] = utcnow()
        _atomic_write(self.path, doc)
        self._doc = doc

    # -- nodes -------------------------------------------------------------
    def node(self, node_id):
        for n in self.doc()["nodes"]:
            if n["id"] == node_id:
                return n
        raise KeyError(f"unknown node {node_id!r}")

    def node_ids(self):
        return [n["id"] for n in self.doc()["nodes"]]

    def add_nodes(self, specs):
        """Append node specs (e.g. per-shot fan-out after shot planning)."""
        doc = self.doc()
        have = {n["id"] for n in doc["nodes"]}
        for spec in specs:
            if spec["id"] in have:
                raise ValueError(f"duplicate node id {spec['id']!r}")
            doc["nodes"].append(spec)
            have.add(spec["id"])
        self.save()

    def set_node(self, node_id, **fields):
        node = self.node(node_id)
        node.update(fields)
        self.save()

    def reset_node(self, node_id, reason=""):
        """Return a node to idle (for retry) — succeeded outputs are kept."""
        node = self.node(node_id)
        node["status"] = d.IDLE
        node["attempts"] = 0
        node["error"] = None
        node["history"].append({"at": utcnow(), "event": "reset",
                                "reason": reason})
        self.save()

    # -- resume helpers ----------------------------------------------------
    def succeeded_outputs(self, node_id):
        """Re-read a succeeded node's persisted outputs (resume support)."""
        node = self.node(node_id)
        if node["status"] != d.SUCCEEDED:
            raise ValueError(f"node {node_id!r} is {node['status']}, not succeeded")
        return dict(node.get("outputs") or {})

    def ready_nodes(self):
        """Idle nodes whose deps all succeeded (topo-ready, in order)."""
        doc = self.doc()
        by_id = {n["id"]: n for n in doc["nodes"]}
        ready = []
        for n in doc["nodes"]:
            if n["status"] != d.IDLE:
                continue
            deps_ok = all(
                by_id.get(dep, {}).get("status") == d.SUCCEEDED
                for dep in n.get("deps", []))
            if deps_ok:
                ready.append(n)
        return ready

    def blocked_nodes(self):
        """Idle nodes whose deps failed — cannot proceed without reset."""
        doc = self.doc()
        by_id = {n["id"]: n for n in doc["nodes"]}
        return [n for n in doc["nodes"]
                if n["status"] == d.IDLE and any(
                    by_id.get(dep, {}).get("status") == d.FAILED
                    for dep in n.get("deps", []))]

    def all_succeeded(self):
        return all(n["status"] == d.SUCCEEDED for n in self.doc()["nodes"])

    def summary(self):
        doc = self.doc()
        counts = {s: 0 for s in d.STATUSES}
        for n in doc["nodes"]:
            counts[n["status"]] = counts.get(n["status"], 0) + 1
        return {"episode": self.episode_id, "status": doc.get("status"),
                "nodes": len(doc["nodes"]), "counts": counts}
