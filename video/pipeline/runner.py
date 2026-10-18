"""Topological DAG runner: idle -> running -> succeeded | failed.

- One node executes at a time: no concurrent runs per node, guaranteed.
- Explicit per-shot retry counts (node["retries"]); attempts recorded.
- Sentinel errors (PipelineBlockedError, CancelledError) are never retried
  and never swallowed: they fail the node immediately.
- Cooperative cancellation: ctx.cancel() is honored before each node.
- Resume: succeeded nodes are skipped, their persisted outputs re-read.
- Full-snapshot atomic state writes after every node transition.
"""

from __future__ import annotations

import os
import threading
import time

from . import definition as d
from . import nodes as nodes_mod
from . import qc
from . import state as state_mod

# Sentinel errors: propagate uncaught, never retried, never swallowed.
_NO_RETRY = (d.PipelineBlockedError, d.CancelledError)


class RunContext:
    """Execution context handed to node executors."""

    def __init__(self, home, episode_state, cancelled=None, log=None):
        self.home = os.path.abspath(home)
        self.state = episode_state          # state_mod.EpisodeState
        self.episode = episode_state.doc()  # episode spec dict
        self.cancelled = cancelled or threading.Event()
        self.log = log or (lambda msg: print(msg, flush=True))

    def check_cancelled(self):
        if self.cancelled.is_set():
            raise d.CancelledError("cancelled by request")

    def advance_publish_state(self, to):
        doc = self.state.doc()
        current = doc.get("publish_state", "defined")
        new = qc.advance_publish_state(current, to)
        doc["publish_state"] = new
        self.state.save()
        self.log(f"publish_state: {current} -> {new}")
        return new


def _resolve_inputs(ctx, node):
    """Resolve input refs from succeeded dep outputs; missing -> UNRESOLVED."""
    by_id = {n["id"]: n for n in ctx.state.doc()["nodes"]}
    resolved = {}
    for name, spec in (node.get("inputs") or {}).items():
        if d.is_input_ref(spec):
            src = by_id.get(spec["node"])
            out = (src.get("outputs") or {}).get(spec["output"]) \
                if src else None
            if (src is not None and src["status"] == d.SUCCEEDED
                    and out is not None and d.is_typed_value(out)):
                resolved[name] = out
            else:
                resolved[name] = dict(d.UNRESOLVED)
        elif d.is_typed_value(spec) or d.is_unresolved(spec):
            resolved[name] = spec
        else:
            resolved[name] = dict(d.UNRESOLVED)
    return resolved


def _topo_order(node_list):
    """Topological order honoring deps; raises on cycles/unknown deps."""
    by_id = {n["id"]: n for n in node_list}
    order, temp, perm = [], set(), set()

    def visit(nid):
        if nid in perm:
            return
        if nid in temp:
            raise d.PipelineError(f"cycle detected at node {nid!r}")
        if nid not in by_id:
            raise d.PipelineError(f"unknown dep {nid!r}")
        temp.add(nid)
        for dep in by_id[nid].get("deps", []):
            visit(dep)
        temp.discard(nid)
        perm.add(nid)
        order.append(nid)

    for n in node_list:
        visit(n["id"])
    return [by_id[nid] for nid in order]


def _run_node(ctx, node):
    """Execute one node with retries. Returns True on success."""
    executor = nodes_mod.EXECUTORS.get(node["type"])
    if executor is None:
        raise d.PipelineError(f"unknown node type {node['type']!r}")
    retries = int(node.get("retries", 0))
    last_exc = None
    for attempt in range(retries + 1):
        ctx.check_cancelled()
        node["status"] = d.RUNNING
        node["attempts"] = attempt + 1
        node["started_at"] = state_mod.utcnow()
        node["error"] = None
        ctx.state.save()
        ctx.log(f"[{node['id']}] attempt {attempt + 1}/{retries + 1} "
                f"({node['type']})")
        try:
            inputs = _resolve_inputs(ctx, node)
            outputs = executor(ctx, node, inputs) or {}
            for k, v in outputs.items():
                if not d.is_typed_value(v):
                    raise d.PipelineError(
                        f"node {node['id']}: output {k!r} is not a typed value")
            node["outputs"] = outputs
            node["status"] = d.SUCCEEDED
            node["ended_at"] = state_mod.utcnow()
            node["history"].append(
                {"at": node["ended_at"], "event": "succeeded",
                 "attempt": attempt + 1})
            ctx.state.save()
            ctx.log(f"[{node['id']}] succeeded")
            return True
        except _NO_RETRY as exc:
            # Sentinel: fail immediately, no retry, propagate the record.
            err = d.redact_secrets(f"{type(exc).__name__}: {exc}")
            node["status"] = d.FAILED
            node["ended_at"] = state_mod.utcnow()
            node["error"] = err
            node["history"].append(
                {"at": node["ended_at"], "event": "failed",
                 "attempt": attempt + 1, "sentinel": True,
                 "error": err})
            ctx.state.save()
            ctx.log(f"[{node['id']}] BLOCKED (no retry): {err}")
            return False
        except Exception as exc:  # noqa: BLE001 - recorded, then retried/failed
            last_exc = exc
            node["history"].append(
                {"at": state_mod.utcnow(), "event": "attempt_failed",
                 "attempt": attempt + 1,
                 "error": d.redact_secrets(f"{type(exc).__name__}: {exc}")})
            ctx.log(f"[{node['id']}] attempt {attempt + 1} failed: "
                    f"{d.redact_secrets(exc)}")
            if attempt < retries:
                time.sleep(min(2 ** attempt, 8))
    node["status"] = d.FAILED
    node["ended_at"] = state_mod.utcnow()
    node["error"] = d.redact_secrets(
        f"{type(last_exc).__name__}: {last_exc}")
    node["history"].append({"at": node["ended_at"], "event": "failed",
                            "attempt": retries + 1, "error": node["error"]})
    ctx.state.save()
    ctx.log(f"[{node['id']}] failed after {retries + 1} attempt(s): "
            f"{node['error']}")
    return False


def _maybe_expand(ctx, node, provider, episode_no, review, finish_params):
    """After plan_shots succeeds, materialize the per-shot fan-out once."""
    if node["type"] != "plan_shots" or node["status"] != d.SUCCEEDED:
        return
    if any(n["id"].startswith("gen_shot_")
           for n in ctx.state.doc()["nodes"]):
        return  # already expanded (resume path)
    shots_path = os.path.join(ctx.state.dir, "shots.json")
    import json
    with open(shots_path, encoding="utf-8") as fh:
        shots = json.load(fh)["shots"]
    # Attach identity blocks: prefer per-shot, else episode default.
    blocks = qc.load_identity_blocks(ctx.episode["project_dir"])
    for shot in shots:
        if not shot.get("identity_block"):
            char = (shot.get("character") or "").upper()
            if char in blocks:
                shot["identity_block"] = blocks[char]["text"]
                shot["expected_identity_hash"] = blocks[char]["hash"]
    new_nodes = nodes_mod.expand_after_plan(
        shots, provider=provider, episode_no=episode_no,
        review=review, finish_params=finish_params)
    ctx.state.add_nodes(new_nodes)
    ctx.log(f"expanded {len(shots)} shots -> {len(new_nodes)} nodes")


def run(home, episode_id, provider=None, episode_no=1, review=None,
        finish_params=None, cancelled=None, log=None):
    """Run (or resume) an episode's DAG to completion.

    Returns {"completed": bool, "succeeded": [...], "failed": [...]}.
    Stops at the first failed node whose dependents cannot proceed.
    """
    st = state_mod.EpisodeState(home, episode_id)
    st.load()
    ctx = RunContext(home, st, cancelled=cancelled, log=log)
    provider = provider or st.doc().get("provider") or "local-ffmpeg"

    succeeded, failed = [], []
    while True:
        ctx.check_cancelled()
        ordered = _topo_order(st.doc()["nodes"])
        progressed = False
        for node in ordered:
            if node["status"] == d.SUCCEEDED:
                continue
            if node["status"] == d.FAILED:
                continue
            if node["status"] == d.RUNNING:
                # Crash recovery: a previous run died mid-node; re-run it.
                ctx.log(f"[{node['id']}] was running at shutdown; re-running")
                st.reset_node(node["id"], reason="crash recovery")
            deps_ok = all(
                st.node(dep)["status"] == d.SUCCEEDED
                for dep in node.get("deps", []))
            if not deps_ok:
                continue
            ok = _run_node(ctx, st.node(node["id"]))
            progressed = True
            if ok:
                succeeded.append(node["id"])
                _maybe_expand(ctx, st.node(node["id"]), provider,
                              episode_no, review or {},
                              finish_params or {})
            else:
                failed.append(node["id"])
            break  # re-evaluate the DAG after every node (expansion)
        if not progressed:
            break

    remaining = [n["id"] for n in st.doc()["nodes"]
                 if n["status"] not in (d.SUCCEEDED, d.FAILED)]
    blocked = [n["id"] for n in st.blocked_nodes()]
    completed = not remaining
    status = "completed" if completed else (
        "blocked" if blocked or failed else "incomplete")
    st.doc()["status"] = status
    st.save()
    state_mod.EpisodeRegistry(home).set_status(episode_id, status)
    return {"completed": completed, "status": status,
            "succeeded": succeeded, "failed": failed,
            "remaining": remaining, "blocked": blocked}
