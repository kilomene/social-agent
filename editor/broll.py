"""B-roll placement planner: given a watch analysis (silence spans / markers
as gap candidates) and a folder of b-roll clips, produce an overlay plan —
picture-in-picture or full cutaway at timestamps — as JSON, and apply it.

Apply modes:
  * cutaway — hard cut to b-roll for `dur` seconds (concat assembly)
  * pip      — b-roll scaled into a corner over the main video (ffmpeg overlay)
"""

import json
import os
import random

from video import ffmpeg as vff

PIP_POSITIONS = {
    "bottom-right": ("W-w-40", "H-h-40"),
    "bottom-left": ("40", "H-h-40"),
    "top-right": ("W-w-40", "40"),
    "top-left": ("40", "40"),
}


def plan(analysis, broll_files, mode="pip", gap_min=1.5, max_items=8,
         position="bottom-right", pip_scale=0.32, seed=7):
    """Build a b-roll plan from analysis silence spans (natural cut points)."""
    if not broll_files:
        raise ValueError("no b-roll files supplied")
    gaps = [(s, e) for s, e in analysis.get("silence_spans", [])
            if e - s >= gap_min][:max_items]
    # fall back to scene cuts if there is no silence
    if not gaps:
        cuts = analysis.get("scene_cuts", [])
        gaps = [(c, c + 3.0) for c in cuts[:max_items]]
    rng = random.Random(seed)  # deterministic
    files = list(broll_files)
    rng.shuffle(files)
    items, used = [], 0
    for i, (s, e) in enumerate(gaps):
        f = files[i % len(files)]
        dur = round(min(e - s, 6.0), 2)
        items.append({"at": round(s, 2), "duration": dur, "file": f,
                      "mode": mode, "position": position,
                      "pip_scale": pip_scale})
        used += 1
    return {"mode": mode, "items": items,
            "note": f"{used} b-roll insert(s) planned from "
                    f"{len(analysis.get('silence_spans', []))} silence gap(s)"}


def save_plan(plan_dict, out_path):
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(plan_dict, fh, indent=2)
    return out_path


def build_apply_pip(input_path, output_path, plan_dict, strict=True):
    """Apply a pip-mode plan as one ffmpeg filter_complex command."""
    items = [it for it in plan_dict.get("items", []) if it["mode"] == "pip"]
    if not items:
        raise ValueError("plan has no pip items to apply")
    if strict and not os.path.exists(input_path):
        raise FileNotFoundError(f"input not found: {input_path!r}")
    for it in items:
        if strict and not os.path.exists(it["file"]):
            raise FileNotFoundError(f"b-roll not found: {it['file']!r}")
    if os.path.abspath(input_path) == os.path.abspath(output_path):
        raise ValueError("refusing: output would overwrite the input")
    argv = [vff.FFMPEG, "-y", "-i", input_path]
    for it in items:
        argv += ["-i", it["file"]]
    x, y = PIP_POSITIONS.get(items[0]["position"], PIP_POSITIONS["bottom-right"])
    filt, last = "", "[0:v]"
    for i, it in enumerate(items, 1):
        sc = it.get("pip_scale", 0.32)
        filt += (f"[{i}:v]scale=iw*{sc}:ih*{sc},"
                 f"setpts=PTS+{it['at']}/TB[pip{i}];")
        filt += (f"{last}[pip{i}]overlay=x='{x}':y='{y}':"
                 f"enable='between(t,{it['at']},{it['at'] + it['duration']})'"
                 f"[v{i}];")
        last = f"[v{i}]"
    filt = filt.rstrip(";")
    return argv + ["-filter_complex", filt, "-map", last, "-map", "0:a?",
                   "-c:v", "libx264", "-preset", "fast", "-crf", "19",
                   "-c:a", "aac", output_path]


def build_apply_cutaway(input_path, output_path, plan_dict, strict=True):
    """Apply a cutaway-mode plan: re-assemble main + b-roll via concat plan."""
    items = sorted([it for it in plan_dict.get("items", []) if it["mode"] == "cutaway"],
                   key=lambda it: it["at"])
    if not items:
        raise ValueError("plan has no cutaway items to apply")
    # Implemented as a JSON edit-plan the caller can inspect: alternating
    # main segments and b-roll inserts. Returned as data, not argv, because
    # it needs intermediate clips.
    seq, cursor = [], 0.0
    for it in items:
        if it["at"] > cursor:
            seq.append({"op": "clip", "source": "main",
                        "start": cursor, "duration": round(it["at"] - cursor, 2)})
        seq.append({"op": "insert", "source": it["file"],
                    "duration": it["duration"]})
        cursor = it["at"] + it["duration"]
    seq.append({"op": "clip", "source": "main", "start": cursor, "duration": None})
    return {"input": input_path, "output": output_path, "sequence": seq,
            "note": "cut main at each insert point, concat in order "
                    "(use `video plan` steps per segment)"}
