"""Visually-lossless-ish compression: CRF ladders per codec with honest
guidance. There is no such thing as truly lossless compression at a smaller
size — "no noticeable loss" here means CRF 18-20 (H.264), 20-23 (HEVC),
23-27 (AV1) at sane presets, verified by eye on the target screen.

Also: 2-pass mode for hitting an exact file-size target (platform upload caps).
"""

import os

from video import ffmpeg as vff

# codec -> {"encoder", "crf_ladder" (best->smallest), "preset"}
CODECS = {
    "h264": {"encoder": "libx264", "ladder": [16, 18, 20, 23],
             "preset": "slow",
             "note": "universal compatibility; CRF 18 ≈ visually transparent"},
    "hevc": {"encoder": "libx265", "ladder": [18, 20, 23, 26],
             "preset": "slow",
             "note": "~40% smaller than h264 at equal quality; slower"},
    "av1": {"encoder": "libsvtav1", "ladder": [22, 25, 28, 32],
            "preset": "6",
            "note": "smallest files; slowest encode; YouTube/Vimeo friendly"},
}


def list_codecs():
    return {k: v["note"] for k, v in CODECS.items()}


def build_crf(input_path, output_path, codec="h264", quality="high", strict=True):
    """Single-pass CRF encode. quality: best|high|balanced|small."""
    if codec not in CODECS:
        raise ValueError(f"unknown codec {codec!r} (pick: {', '.join(CODECS)})")
    vff._guard(input_path, output_path, strict)
    c = CODECS[codec]
    idx = {"best": 0, "high": 1, "balanced": 2, "small": 3}[quality]
    crf = c["ladder"][idx]
    argv = [vff.FFMPEG, "-y", "-i", input_path, "-c:v", c["encoder"],
            "-preset", c["preset"], "-crf", str(crf)]
    return argv + ["-c:a", "aac", "-b:a", "160k", output_path]


def build_twopass(input_path, output_path, target_mb, codec="h264", strict=True):
    """2-pass encode aimed at an exact file size (platform caps)."""
    import os as _os
    if codec not in CODECS:
        raise ValueError(f"unknown codec {codec!r}")
    vff._guard(input_path, output_path, strict)
    info = vff.info(input_path)
    dur = max(1.0, info.get("duration", 60))
    # bitrate budget: (MB*8/duration) minus 160k audio, in kbit/s
    vbitrate = max(400, int(target_mb * 8192 / dur) - 160)
    c = CODECS[codec]
    passlog = output_path + ".2pass.log"
    common = ["-c:v", c["encoder"], "-preset", c["preset"],
              "-b:v", f"{vbitrate}k", "-c:a", "aac", "-b:a", "160k"]
    p1 = ([vff.FFMPEG, "-y", "-i", input_path] + common +
          ["-pass", "1", "-passlogfile", passlog, "-f", "mp4", "/dev/null"])
    p2 = ([vff.FFMPEG, "-y", "-i", input_path] + common +
          ["-pass", "2", "-passlogfile", passlog, output_path])
    return [p1, p2]
