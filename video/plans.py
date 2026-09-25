"""Edit plans: stored clip/trim/concat/filter step lists executed in order.

A plan is JSON: {"name": ..., "steps": [{"op": "clip", "start": 2,
"duration": 10}, {"op": "to-vertical"}, ...], "created": ...}.
Stored in <home>/video_plans/<name>.json. `run` executes each step,
chaining temp intermediates, and writes the final output.
"""

import json
import os
import tempfile
from datetime import datetime, timezone

from . import ffmpeg as ff

PLANS_DIR = "video_plans"

# op -> (builder kwargs taken from step, needs_input)
_STEP_BUILDERS = {
    "clip": ("build_clip", ["start", "duration"]),
    "trim": ("build_trim", ["start", "end"]),
    "to-vertical": ("build_to_vertical", []),
    "to-horizontal": ("build_to_horizontal", []),
    "compress": ("build_compress", ["preset"]),
}


def plans_dir(home):
    return os.path.join(home, PLANS_DIR)


def create(home, name, steps, description=""):
    """Validate + store a plan. steps: list of {"op": ..., ...} dicts."""
    if not name or "/" in name or name.startswith("."):
        raise ValueError(f"bad plan name {name!r}")
    if not isinstance(steps, list) or not steps:
        raise ValueError("plan needs a non-empty steps list")
    for i, s in enumerate(steps):
        if not isinstance(s, dict) or s.get("op") not in _STEP_BUILDERS:
            raise ValueError(
                f"step {i}: unknown op {s.get('op')!r} "
                f"(pick: {', '.join(sorted(_STEP_BUILDERS))})")
    plan = {"name": name, "description": description, "steps": steps,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    d = plans_dir(home)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{name}.json")
    if os.path.exists(p):
        raise ValueError(f"plan {name!r} already exists")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, indent=2)
    return plan


def load(home, name):
    p = os.path.join(plans_dir(home), f"{name}.json")
    if not os.path.exists(p):
        raise ValueError(f"unknown plan {name!r}")
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def list_plans(home):
    d = plans_dir(home)
    if not os.path.isdir(d):
        return []
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))


def run(home, name, input_path, output_path, dry_run=False):
    """Execute a plan's steps in order; returns the final output path."""
    plan = load(home, name)
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"input not found: {input_path!r}")
    if os.path.abspath(input_path) == os.path.abspath(output_path):
        raise ValueError("refusing: output would overwrite the input")
    current = input_path
    tmpdir = tempfile.mkdtemp(prefix="sa-plan-")
    try:
        for i, step in enumerate(plan["steps"]):
            op = step["op"]
            builder_name, keys = _STEP_BUILDERS[op]
            builder = getattr(ff, builder_name)
            kwargs = {k: step[k] for k in keys if k in step}
            kwargs["strict"] = not dry_run
            is_last = i == len(plan["steps"]) - 1
            out = output_path if is_last else os.path.join(
                tmpdir, f"step{i}.mp4")
            argv = builder(current, out, **kwargs)
            ff.run_cmd(argv, dry_run=dry_run)
            current = out
    finally:
        # keep intermediates only for real runs (debuggable), drop on dry-run
        if dry_run:
            for f in os.listdir(tmpdir):
                os.remove(os.path.join(tmpdir, f))
            os.rmdir(tmpdir)
    return output_path
