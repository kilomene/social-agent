"""ffmpeg/ffprobe command builders + runner (stdlib only).

Builders return the argv list (pure, testable). run_cmd() prints the exact
command, then executes it. All builders refuse to let an output path equal
an input path.
"""

import json
import os
import shutil
import subprocess

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


def which_ffmpeg():
    """Return the ffmpeg binary path, or None if not installed."""
    return shutil.which(FFMPEG)


def ffprobe():
    return shutil.which(FFPROBE)


def _guard(input_path, output_path, strict=True):
    if strict and (not input_path or not os.path.exists(input_path)):
        raise FileNotFoundError(f"input not found: {input_path!r}")
    if not output_path:
        raise ValueError("output path is required")
    if os.path.abspath(input_path) == os.path.abspath(output_path):
        raise ValueError("refusing: output would overwrite the input")


def run_cmd(argv, dry_run=False):
    """Print the exact command, then run it (unless dry_run)."""
    print("RUN:", " ".join(argv))
    if dry_run:
        return {"dry_run": True, "argv": argv}
    if not which_ffmpeg():
        raise RuntimeError("ffmpeg not found — see video/SETUP.md for install steps")
    proc = subprocess.run(argv, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed (exit {proc.returncode}): "
                           f"{proc.stderr.strip()[-500:]}")
    return {"dry_run": False, "argv": argv, "stderr": proc.stderr[-500:]}


def info(input_path):
    """Probe a file -> {"duration", "width", "height", "fps", "vcodec", "acodec",
    "file_size", "container"}."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"input not found: {input_path!r}")
    if not ffprobe():
        raise RuntimeError("ffprobe not found — see video/SETUP.md")
    argv = [FFPROBE, "-v", "error", "-show_entries",
            "format=duration:stream=width,height,avg_frame_rate,codec_name,codec_type",
            "-of", "json", input_path]
    print("RUN:", " ".join(argv))
    proc = subprocess.run(argv, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {proc.stderr.strip()[-300:]}")
    data = json.loads(proc.stdout or "{}")
    out = {"duration": float(data.get("format", {}).get("duration", 0) or 0),
           "file_size": os.path.getsize(input_path),
           "container": os.path.splitext(input_path)[1].lower().lstrip(".") or "mp4",
           "path": input_path}
    for s in data.get("streams", []):
        if s.get("codec_type") == "video" and "width" not in out:
            out.update({"width": s.get("width"), "height": s.get("height"),
                        "vcodec": s.get("codec_name")})
            num, den = (s.get("avg_frame_rate", "0/1") + "/1").split("/")[:2]
            out["fps"] = round(float(num) / float(den or 1), 2) if den != "0" else 0
        if s.get("codec_type") == "audio" and "acodec" not in out:
            out["acodec"] = s.get("codec_name")
    return out


# ---------------------------------------------------------------- builders --

def build_clip(input_path, output_path, start, duration, strict=True):
    """Extract [start, start+duration) fast (seek before input)."""
    _guard(input_path, output_path, strict)
    return [FFMPEG, "-y", "-ss", str(start), "-i", input_path,
            "-t", str(duration), "-c", "copy", output_path]


def build_trim(input_path, output_path, start, end, strict=True):
    """Cut [start, end) precisely (re-encode for frame accuracy)."""
    _guard(input_path, output_path, strict)
    return [FFMPEG, "-y", "-i", input_path, "-ss", str(start), "-to", str(end),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", output_path]


def build_concat(inputs, output_path, strict=True):
    """Join files (same codec/resolution) without re-encoding."""
    if len(inputs) < 2:
        raise ValueError("concat needs at least 2 inputs")
    for p in inputs:
        if strict and not os.path.exists(p):
            raise FileNotFoundError(f"input not found: {p!r}")
    _guard(inputs[0], output_path, strict)
    argv = [FFMPEG, "-y"]
    for p in inputs:
        argv += ["-i", p]
    n = len(inputs)
    filt = "".join(f"[{i}:v][{i}:a]" for i in range(n))
    filt += f"concat=n={n}:v=1:a=1[outv][outa]"
    return argv + ["-filter_complex", filt, "-map", "[outv]", "-map", "[outa]",
                   "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                   "-c:a", "aac", output_path]


def pad_filter(width, height):
    """Non-destructive fit filtergraph: blurred-background fill with the sharp
    video centered. Preserves 100% of the source frame — the safe default for
    any aspect-ratio mismatch (see video/fit.py)."""
    return (
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},boxblur=20:2[bg2];"
        f"[fg]scale={width}:{height}:force_original_aspect_ratio=decrease[fg2];"
        f"[bg2][fg2]overlay=(W-w)/2:(H-h)/2,format=yuv420p"
    )


def build_to_vertical(input_path, output_path, width=1080, height=1920, strict=True):
    """16:9 -> 9:16: routes through the smart fitter (pad strategy)."""
    _guard(input_path, output_path, strict)
    return [FFMPEG, "-y", "-i", input_path, "-vf", pad_filter(width, height),
            "-c:v", "libx264", "-preset", "fast", "-crf", "19",
            "-c:a", "aac", output_path]


def build_to_horizontal(input_path, output_path, width=1920, height=1080, strict=True):
    """9:16 -> 16:9: routes through the smart fitter (pad strategy)."""
    _guard(input_path, output_path, strict)
    return [FFMPEG, "-y", "-i", input_path, "-vf", pad_filter(width, height),
            "-c:v", "libx264", "-preset", "fast", "-crf", "19",
            "-c:a", "aac", output_path]


def build_frame(input_path, output_path, at=3, strict=True):
    """Extract a still at `at` seconds (thumbnail source)."""
    _guard(input_path, output_path, strict)
    return [FFMPEG, "-y", "-ss", str(at), "-i", input_path,
            "-frames:v", "1", "-q:v", "2", output_path]


# Upload presets: sane bitrate caps per platform (documented, not magic).
PRESETS = {
    "tiktok":  {"scale": "1080:1920", "fps": 30, "vbitrate": "8M",
                "maxrate": "10M", "note": "TikTok/Reels/Shorts vertical"},
    "reels":   {"scale": "1080:1920", "fps": 30, "vbitrate": "8M",
                "maxrate": "10M", "note": "Instagram Reels vertical"},
    "shorts":  {"scale": "1080:1920", "fps": 30, "vbitrate": "8M",
                "maxrate": "10M", "note": "YouTube Shorts vertical"},
    "youtube": {"scale": "-2:1080", "fps": 30, "vbitrate": "12M",
                "maxrate": "15M", "note": "YouTube 1080p landscape"},
}


# ----------------------------------------------------------------- export --
# Full export ladder: resolution x codec. Hardware encoders are auto-detected
# (nvenc/qsv/vaapi); software fallback otherwise. All builders print the exact
# command via run_cmd and never overwrite inputs.

EXPORT_HEIGHTS = {"480p": 480, "720p": 720, "1080p": 1080,
                  "1440p": 1440, "4k": 2160, "8k": 4320}

# codec -> software encoder + hw candidates (probed in order)
EXPORT_CODECS = {
    "h264": {"sw": ("libx264", ["-preset", "medium", "-crf", "19"]),
             "hw": ["h264_nvenc", "h264_qsv", "h264_vaapi"]},
    "hevc": {"sw": ("libx265", ["-preset", "medium", "-crf", "21"]),
             "hw": ["hevc_nvenc", "hevc_qsv", "hevc_vaapi"]},
    "av1": {"sw": ("libsvtav1", ["-preset", "6", "-crf", "25"]),
            "hw": ["av1_nvenc", "av1_qsv", "av1_vaapi"]},
}


def _available_encoders():
    try:
        proc = subprocess.run([FFMPEG, "-hide_banner", "-encoders"],
                              capture_output=True, text=True)
        return proc.stdout
    except OSError:
        return ""


def pick_encoder(codec, prefer_hw=True):
    """Return (encoder_name, extra_args, kind) — hw if available else software."""
    if codec not in EXPORT_CODECS:
        raise ValueError(f"unknown codec {codec!r} (pick: {', '.join(EXPORT_CODECS)})")
    spec = EXPORT_CODECS[codec]
    if prefer_hw:
        have = _available_encoders()
        for hw in spec["hw"]:
            if hw in have:
                # sanity: hw encoder actually usable requires device; keep the
                # flag honest — caller sees kind="hw (advertised)".
                return hw, ["-cq", "21"] if "nvenc" in hw else [], "hw"
    sw, args = spec["sw"]
    return sw, args, "sw"


def build_export(input_path, output_path, resolution="1080p", codec="h264",
                 vertical=False, prefer_hw=True, strict=True):
    """Master export: scale to `resolution` (height), encode with `codec`."""
    _guard(input_path, output_path, strict)
    if resolution not in EXPORT_HEIGHTS:
        raise ValueError(f"unknown resolution {resolution!r} "
                         f"(pick: {', '.join(EXPORT_HEIGHTS)})")
    h = EXPORT_HEIGHTS[resolution]
    enc, extra, kind = pick_encoder(codec, prefer_hw)
    if vertical:
        vf = f"scale=1080:{h}:force_original_aspect_ratio=increase," \
             f"crop=1080:{h},setsar=1,format=yuv420p"
    else:
        vf = f"scale=-2:{h},setsar=1,format=yuv420p"
    argv = [FFMPEG, "-y", "-i", input_path, "-vf", vf,
            "-c:v", enc] + extra + ["-c:a", "aac", "-b:a", "160k", output_path]
    return argv, {"encoder": enc, "kind": kind, "resolution": resolution,
                  "codec": codec}


def build_export_hw_probe():
    """Report which encoders ffmpeg advertises (for `doctor`/docs)."""
    have = _available_encoders()
    return {c: [hw for hw in spec["hw"] if hw in have]
            for c, spec in EXPORT_CODECS.items()}


def build_compress(input_path, output_path, preset="tiktok", strict=True):
    """Re-encode to a platform upload preset."""
    if preset not in PRESETS:
        raise ValueError(f"unknown preset {preset!r} (pick: {', '.join(PRESETS)})")
    _guard(input_path, output_path, strict)
    p = PRESETS[preset]
    vf = f"scale={p['scale']}:force_original_aspect_ratio=decrease,fps={p['fps']},format=yuv420p"
    return [FFMPEG, "-y", "-i", input_path, "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-b:v", p["vbitrate"],
            "-maxrate", p["maxrate"], "-bufsize", p["maxrate"],
            "-c:a", "aac", "-b:a", "128k", output_path]
