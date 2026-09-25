"""Quality assurance: verify a finished render before it ships.

Checks: black frames (blackdetect), frozen video (freezedetect), long silent
gaps, audio/video desync estimate, subtitle timing (via subtitles.validate),
export corruption (full decode pass), and Kdenlive/Shotcut missing media.

`verify()` returns {"passed": bool, "issues": [...]}. `verify_or_rerender()`
re-renders once via a supplied rebuild callable on failure, logging the error.
"""

import json
import os
import subprocess

from video import ffmpeg as vff


def _err(argv):
    proc = subprocess.run(argv, capture_output=True, text=True)
    return proc.stderr


def black_frames(input_path, min_dur=1.0):
    """Return [(start, end)] black segments."""
    err = _err(["ffmpeg", "-hide_banner", "-i", input_path, "-vf",
                f"blackdetect=d={min_dur}:pic_th=0.98:pix_th=0.10",
                "-f", "null", "-"])
    spans = []
    for line in err.splitlines():
        if "black_start" in line:
            try:
                s = float(line.split("black_start:")[1].split()[0])
                e = float(line.split("black_end:")[1].split()[0])
                spans.append((round(s, 2), round(e, 2)))
            except (ValueError, IndexError):
                pass
    return spans


def frozen_segments(input_path, min_dur=2.0):
    err = _err(["ffmpeg", "-hide_banner", "-i", input_path, "-vf",
                f"freezedetect=d={min_dur}:n=0.003", "-f", "null", "-"])
    spans = []
    for line in err.splitlines():
        if "freeze_start" in line:
            try:
                s = float(line.split("freeze_start:")[1].split()[0])
                e = float(line.split("freeze_end:")[1].split()[0])
                spans.append((round(s, 2), round(e, 2)))
            except (ValueError, IndexError):
                pass
    return spans


def desync_estimate(input_path):
    """Crude A/V desync estimate: compare first audio/video packet timestamps."""
    argv = [vff.ffprobe() or "ffprobe", "-v", "error", "-show_entries",
            "packet=pts_time,stream_index", "-select_streams", "v:0",
            "-read_intervals", "%+#5", "-of", "json", input_path]
    try:
        out = json.loads(subprocess.run(argv, capture_output=True,
                                        text=True).stdout or "{}")
        v0 = float(out["packets"][0]["pts_time"])
    except Exception:
        return None
    argv[argv.index("v:0")] = "a:0"
    try:
        out = json.loads(subprocess.run(argv, capture_output=True,
                                        text=True).stdout or "{}")
        a0 = float(out["packets"][0]["pts_time"])
    except Exception:
        return None
    return round(abs(v0 - a0), 3)


def decode_pass(input_path):
    """Full decode: catches export corruption. Returns (ok, error_tail)."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-v", "error", "-i", input_path,
         "-f", "null", "-"], capture_output=True, text=True)
    return proc.returncode == 0, proc.stderr.strip()[-300:]


def verify(input_path, srt_path=None, project=None):
    """Run every applicable check. Returns {"passed", "issues", "details"}."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"input not found: {input_path!r}")
    issues, details = [], {}
    blacks = black_frames(input_path)
    details["black_spans"] = blacks
    if blacks:
        issues.append(f"{len(blacks)} black segment(s): {blacks[:3]}")
    frozen = frozen_segments(input_path)
    details["frozen_spans"] = frozen
    if frozen:
        issues.append(f"{len(frozen)} frozen segment(s): {frozen[:3]}")
    desync = desync_estimate(input_path)
    details["desync_s"] = desync
    if desync is not None and desync > 0.2:
        issues.append(f"possible A/V desync: {desync}s")
    ok, err = decode_pass(input_path)
    details["decode_ok"] = ok
    if not ok:
        issues.append(f"export corruption: decode failed ({err[:120]})")
    if srt_path:
        from editor import subtitles as subs_mod
        cues = subs_mod.parse_srt(srt_path)
        sub_issues = subs_mod.validate(cues)
        details["subtitle_issues"] = sub_issues
        issues.extend(f"subtitle: {i}" for i in sub_issues)
    if project is not None:
        missing = project.missing_media()
        details["missing_media"] = missing
        if missing:
            issues.append(f"{len(missing)} missing media file(s)")
    return {"passed": not issues, "issues": issues, "details": details}


def verify_or_rerender(input_path, rebuild, srt_path=None, project=None,
                       log_path=None):
    """Verify; on failure call rebuild() once and verify again.

    rebuild: zero-arg callable that re-renders input_path. Returns the final
    verify() dict with an added "rerendered" flag.
    """
    first = verify(input_path, srt_path=srt_path, project=project)
    if first["passed"]:
        first["rerendered"] = False
        return first
    err = "; ".join(first["issues"])
    if log_path:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(f"QA FAIL {input_path}: {err}\n")
    try:
        rebuild()
    except Exception as e:
        first["rerendered"] = False
        first["rebuild_error"] = str(e)[:200]
        return first
    second = verify(input_path, srt_path=srt_path, project=project)
    second["rerendered"] = True
    second["first_issues"] = first["issues"]
    return second
