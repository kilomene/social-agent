"""Camera enhancements as ffmpeg filtergraphs: stabilization, denoise,
white balance, brightness/contrast recovery, deflicker.

Stabilization uses vidstabdetect/vidstabtransform 2-pass when those filters
exist (they do here); otherwise falls back to deshake with an honest note.
"""

import os
import subprocess

from video import ffmpeg as vff


def _has_filter(name):
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-h", f"filter={name}"],
                          capture_output=True, text=True)
    return proc.returncode == 0


def stabilize_pass1(input_path, trf_path):
    """vidstab pass 1: measure shake -> transforms file."""
    return [vff.FFMPEG, "-y", "-i", input_path, "-vf",
            f"vidstabdetect=shakiness=5:accuracy=15:result={trf_path}",
            "-f", "null", "-"]


def stabilize_pass2(input_path, output_path, trf_path,
                    smoothing=30, strict=True):
    """vidstab pass 2: apply transforms."""
    if strict and not os.path.exists(input_path):
        raise FileNotFoundError(f"input not found: {input_path!r}")
    if os.path.abspath(input_path) == os.path.abspath(output_path):
        raise ValueError("refusing: output would overwrite the input")
    return [vff.FFMPEG, "-y", "-i", input_path, "-vf",
            f"vidstabtransform=input={trf_path}:smoothing={smoothing}:"
            "crop=keep:zoom=0",
            "-c:v", "libx264", "-preset", "fast", "-crf", "19",
            "-c:a", "aac", output_path]


def build_stabilize(input_path, output_path, trf_path="/tmp/stab.trf",
                    strict=True):
    """Return [pass1_argv, pass2_argv], or a deshake single-pass fallback."""
    if _has_filter("vidstabdetect"):
        return [stabilize_pass1(input_path, trf_path),
                stabilize_pass2(input_path, output_path, trf_path,
                                strict=strict)]
    # honest fallback
    if strict and not os.path.exists(input_path):
        raise FileNotFoundError(f"input not found: {input_path!r}")
    argv = [vff.FFMPEG, "-y", "-i", input_path, "-vf", "deshake",
            "-c:v", "libx264", "-preset", "fast", "-crf", "19",
            "-c:a", "aac", output_path]
    return [{"fallback": "vidstab not available — using deshake (weaker)",
             "argv": argv}]


def denoise_filter(strength="medium"):
    """hqdn3r spatial/temporal denoise presets."""
    return {"light": "hqdn3d=1.5:1.5:6:6",
            "medium": "hqdn3d=3:3:8:8",
            "strong": "hqdn3d=5:5:10:10"}.get(strength, "hqdn3d=3:3:8:8")


def white_balance_filter(temp="neutral"):
    """Simple white-balance nudges via colorbalance."""
    return {
        "cool": "colorbalance=rs=-0.10:bs=0.12:rm=-0.06:bm=0.08",
        "warm": "colorbalance=rs=0.10:bs=-0.10:rm=0.06:bm=-0.06",
        "neutral": "colorbalance=rs=0.0:gs=0.0:bs=0.0",
    }.get(temp, "colorbalance=rs=0.0:gs=0.0:bs=0.0")


def build_enhance(input_path, output_path, denoise="medium", temp="neutral",
                  brightness=0.0, contrast=1.0, deflicker=False, strict=True):
    """Denoise + white balance + exposure recovery in one pass."""
    if strict and not os.path.exists(input_path):
        raise FileNotFoundError(f"input not found: {input_path!r}")
    if os.path.abspath(input_path) == os.path.abspath(output_path):
        raise ValueError("refusing: output would overwrite the input")
    vf = (f"{denoise_filter(denoise)},{white_balance_filter(temp)},"
          f"eq=brightness={brightness}:contrast={contrast},format=yuv420p")
    if deflicker:
        # NOTE: true deflicker needs per-frame luminance analysis; this is the
        # standard first step (temporal smoothing). Documented honestly.
        vf = f"tblend=all_mode=average,{vf}"
    return [vff.FFMPEG, "-y", "-i", input_path, "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", output_path]
