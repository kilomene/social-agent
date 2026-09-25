"""Audio command builders (pure functions) + runner (stdlib only).

Builders return the ffmpeg argv list. The CLI prints the exact command via
run_cmd() before executing, and refuses to overwrite inputs.
"""

import os
import subprocess

from video import ffmpeg as vff

FFMPEG = "ffmpeg"


def _guard_in(path, strict=True):
    if strict and (not path or not os.path.exists(path)):
        raise FileNotFoundError(f"input not found: {path!r}")


def _guard(input_path, output_path, strict=True):
    _guard_in(input_path, strict)
    if not output_path:
        raise ValueError("output path is required")
    if os.path.abspath(input_path) == os.path.abspath(output_path):
        raise ValueError("refusing: output would overwrite the input")


def run_cmd(argv, dry_run=False):
    return vff.run_cmd(argv, dry_run=dry_run)


def build_clip(input_path, output_path, start, duration, fade_in=0, fade_out=0, strict=True):
    """Clip audio with optional fades (seconds)."""
    _guard(input_path, output_path, strict)
    filt = []
    if float(fade_in) > 0:
        filt.append(f"afade=t=in:st=0:d={fade_in}")
    if float(fade_out) > 0:
        filt.append(f"afade=t=out:st={float(duration) - float(fade_out)}:d={fade_out}")
    argv = [FFMPEG, "-y", "-ss", str(start), "-i", input_path, "-t", str(duration)]
    if filt:
        argv += ["-af", ",".join(filt)]
    return argv + ["-c:a", "libmp3lame", "-b:a", "192k", output_path]


def build_loop(input_path, output_path, duration, strict=True):
    """Loop audio until it fills `duration` seconds."""
    _guard(input_path, output_path, strict)
    return [FFMPEG, "-y", "-stream_loop", "-1", "-i", input_path,
            "-t", str(duration), "-c:a", "libmp3lame", "-b:a", "192k",
            output_path]


def build_mix(voiceover_path, bed_path, output_path, duck_db=12, strict=True):
    """Talking-head mix: music bed ducked under the voiceover.

    Uses sidechain compression so the bed drops while the voice speaks and
    swells back in pauses. duck_db controls how far the bed drops.
    """
    _guard_in(voiceover_path, strict)
    _guard_in(bed_path, strict)
    if not output_path:
        raise ValueError("output path is required")
    for p in (voiceover_path, bed_path):
        if os.path.abspath(p) == os.path.abspath(output_path):
            raise ValueError("refusing: output would overwrite the input")
    # duck_db maps to a static bed reduction (10^(-dB/20)) applied before the
    # sidechain pump, so the bed sits duck_db below full while the voice is
    # the compression key: audible ducking that survives any input levels.
    import math
    bed_gain = 10 ** (-float(duck_db) / 20.0)
    filt = (
        f"[1:a]volume={bed_gain:.4f},asplit=2[bed_sc][bed_mix];"
        "[bed_sc][0:a]sidechaincompress=threshold=0.02:ratio=20:"
        "attack=200:release=800[ducked];"
        "[ducked][bed_mix]amix=inputs=2:duration=shortest:dropout_transition=0,"
        "volume=1.0[mixout]"
    )
    return [FFMPEG, "-y", "-i", voiceover_path, "-i", bed_path,
            "-filter_complex", filt, "-map", "[mixout]",
            "-c:a", "libmp3lame", "-b:a", "192k", output_path]


def build_extract(video_path, output_path, strict=True):
    """Pull the audio track out of a video file."""
    _guard(video_path, output_path, strict)
    return [FFMPEG, "-y", "-i", video_path, "-vn",
            "-c:a", "libmp3lame", "-b:a", "192k", output_path]


# Platform loudness norms (LUFS-ish targets via loudnorm; documented values).
LOUDNESS_TARGETS = {
    "tiktok":  {"I": -14, "TP": -1.5, "LRA": 11, "note": "short-form speech/music"},
    "youtube": {"I": -14, "TP": -1.5, "LRA": 11, "note": "YouTube normalizes ~-14 LUFS"},
    "podcast": {"I": -16, "TP": -1.5, "LRA": 11, "note": "spoken-word standard"},
}


def build_normalize(input_path, output_path, preset="tiktok", strict=True):
    """Two-pass loudness normalization to a platform target."""
    if preset not in LOUDNESS_TARGETS:
        raise ValueError(f"unknown preset {preset!r} "
                         f"(pick: {', '.join(LOUDNESS_TARGETS)})")
    _guard(input_path, output_path, strict)
    t = LOUDNESS_TARGETS[preset]
    filt = f"loudnorm=I={t['I']}:TP={t['TP']}:LRA={t['LRA']}"
    return [FFMPEG, "-y", "-i", input_path, "-af", filt,
            "-c:a", "libmp3lame", "-b:a", "192k", output_path]
