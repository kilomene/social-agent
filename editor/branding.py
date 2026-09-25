"""Brand kit: one YAML file per account keeps every video visually consistent
(logo, colors, fonts, default grade, caption style, intro/outro text).

`brand apply` stamps the kit onto an edit job: grade + captions + intro/outro
+ logo watermark, all from the same source of truth.
"""

import json
import os

from policy import yaml_lite

KIT_DIR = "branding"
DEFAULT_KIT = {
    "name": "My Channel",
    "tagline": "",
    "logo": "",            # path to logo PNG (transparent)
    "colors": {"bg": [8, 12, 16], "fg": [255, 255, 255], "accent": [45, 200, 190]},
    "font": "DejaVuSans-Bold.ttf",
    "grade": "teal-noir",  # default cinematic grade (or "clean" for no effect)
    "caption_style": "pop",
    "intro_text": "Welcome back",
    "outro_text": "Thanks for watching — subscribe",
    "watermark": {"enabled": True, "position": "top-right", "opacity": 0.7,
                  "scale": 0.12},
}


def _yaml_scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if not s or any(c in s for c in ":#'\"{}[]&*!|>@`"):
        return json.dumps(s)
    return s


def _dump_yaml(data, indent=0):
    """Minimal block-style YAML writer for the kit schema (yaml_lite parses it)."""
    lines = []
    pad = "  " * indent
    for k, v in data.items():
        if isinstance(v, dict):
            lines.append(f"{pad}{k}:")
            lines.append(_dump_yaml(v, indent + 1))
        elif isinstance(v, list):
            # block-style: yaml_lite cannot parse flow-style [a, b] lists
            lines.append(f"{pad}{k}:")
            for i in v:
                lines.append(f"{pad}  - {_yaml_scalar(i)}")
        else:
            lines.append(f"{pad}{k}: {_yaml_scalar(v)}")
    return "\n".join(lines)


def kit_path(home, label="default"):
    d = os.path.join(home, KIT_DIR)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{label}.yaml")


def create(home, label="default", **overrides):
    """Write a brand kit (defaults + overrides)."""
    kit = dict(DEFAULT_KIT)
    kit["colors"] = dict(DEFAULT_KIT["colors"])
    kit["watermark"] = dict(DEFAULT_KIT["watermark"])
    for k, v in overrides.items():
        kit[k] = v
    p = kit_path(home, label)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(_dump_yaml(kit) + "\n")
    return p


def load(home, label="default"):
    p = kit_path(home, label)
    if not os.path.exists(p):
        raise FileNotFoundError(f"no brand kit {label!r} — run `brand create` first")
    with open(p, encoding="utf-8") as fh:
        return yaml_lite.loads(fh.read())


def list_kits(home):
    d = os.path.join(home, KIT_DIR)
    if not os.path.isdir(d):
        return []
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".yaml"))


def watermark_filter(logo_path, position="top-right", opacity=0.7, scale=0.12):
    """ffmpeg filter_complex snippet: logo overlay for the whole duration."""
    pos = {"top-right": ("W-w-40", "40"), "top-left": ("40", "40"),
           "bottom-right": ("W-w-40", "H-h-40"),
           "bottom-left": ("40", "H-h-40")}.get(position, ("W-w-40", "40"))
    return {"inputs": ["-i", logo_path],
            "filter": (f"[1:v]scale=iw*{scale}:ih*{scale},"
                       f"format=rgba,colorchannelmixer=aa={opacity}[logo];"
                       f"[0:v][logo]overlay=x='{pos[0]}':y='{pos[1]}'[vout]"),
            "map": "[vout]"}


def apply_plan(input_path, output_path, kit, workdir=None):
    """Build the full branded render as data: grade + watermark (+ captions
    and intro/outro are separate steps the caller chains). Returns a dict
    describing the ffmpeg invocation pieces."""
    from editor import grading as grading_mod
    grade = kit.get("grade", "clean")
    vf = grading_mod.filtergraph(grade)
    wm = kit.get("watermark", {})
    plan = {"input": input_path, "output": output_path, "grade": grade,
            "video_filter": vf, "watermark": None}
    logo = kit.get("logo", "")
    if wm.get("enabled") and logo and os.path.exists(logo):
        plan["watermark"] = watermark_filter(
            logo, wm.get("position", "top-right"),
            wm.get("opacity", 0.7), wm.get("scale", 0.12))
    return plan


def build_apply(input_path, output_path, kit, strict=True):
    """Build the actual ffmpeg argv for grade + watermark in one pass."""
    from editor import grading as grading_mod
    from video import ffmpeg as vff
    if strict and not os.path.exists(input_path):
        raise FileNotFoundError(f"input not found: {input_path!r}")
    if os.path.abspath(input_path) == os.path.abspath(output_path):
        raise ValueError("refusing: output would overwrite the input")
    grade = kit.get("grade", "clean")
    vf = grading_mod.filtergraph(grade)
    wm = kit.get("watermark", {})
    logo = kit.get("logo", "")
    if wm.get("enabled") and logo and os.path.exists(logo):
        w = watermark_filter(logo, wm.get("position", "top-right"),
                             wm.get("opacity", 0.7), wm.get("scale", 0.12))
        argv = [vff.FFMPEG, "-y", "-i", input_path] + w["inputs"]
        filt = f"[0:v]{vf},format=rgba[v0];" + w["filter"].replace("[0:v]", "[v0]")
        argv += ["-filter_complex", filt, "-map", w["map"], "-map", "0:a?",
                 "-c:v", "libx264", "-preset", "fast", "-crf", "19",
                 "-c:a", "aac", output_path]
    else:
        argv = [vff.FFMPEG, "-y", "-i", input_path, "-vf", vf,
                "-c:v", "libx264", "-preset", "fast", "-crf", "19",
                "-c:a", "aac", output_path]
    return argv
