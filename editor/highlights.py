"""Auto highlight detection: combines audio energy peaks with scene cuts to
rank the most exciting segments of a long video, then cuts clips.

Score per candidate segment = normalized audio energy + scene-change density
bonus. Returns ranked [{"start", "end", "score", "reason"}].
"""

import json
import os

from editor import analyze as watch_mod
from video import ffmpeg as vff


def find_highlights(analysis, min_len=3.0, max_len=60.0, top_n=5,
                    window=5.0, step=2.5):
    """Rank highlight segments from a watch analysis dict.

    Candidates = scene-cut-bounded segments + sliding fixed windows (so a
    loud moment inside a long static scene is still found). Overlapping
    candidates go through non-max suppression: highest score wins.
    """
    dur = analysis.get("duration", 0)
    energy = analysis.get("energy_curve", []) or []
    cuts = analysis.get("scene_cuts", []) or []
    if dur <= 0:
        return []

    def score_seg(s, e):
        lo, hi = int(s), min(len(energy), int(e) + 1)
        seg_e = energy[lo:hi] if lo < len(energy) else []
        mean_e = sum(seg_e) / len(seg_e) if seg_e else 0.0
        cut_density = sum(1 for c in cuts if s <= c <= e) / max(1.0, e - s)
        score = round(0.7 * mean_e + 0.3 * min(1.0, cut_density * 2), 3)
        return score, (f"energy={mean_e:.2f} cuts={cut_density:.2f}/s")

    candidates = []
    # 1) scene-bounded segments (split if longer than max_len)
    bounds = [0.0] + sorted(cuts) + [dur]
    for a, b in zip(bounds, bounds[1:]):
        t = a
        while t < b:
            e = min(b, t + max_len)
            if e - t >= min_len:
                candidates.append((round(t, 2), round(e, 2)))
            t = e
    # 2) sliding windows to catch loud moments inside long scenes
    t = 0.0
    while t + min_len <= dur:
        e = min(dur, t + window)
        candidates.append((round(t, 2), round(e, 2)))
        t += step

    scored = []
    for s, e in candidates:
        sc, reason = score_seg(s, e)
        scored.append({"start": s, "end": e, "score": sc, "reason": reason})
    scored.sort(key=lambda r: r["score"], reverse=True)

    # non-max suppression: keep a candidate only if it overlaps <50% with
    # every already-kept (higher-scoring) segment
    kept = []
    for c in scored:
        overlap = False
        for k in kept:
            inter = max(0.0, min(c["end"], k["end"]) - max(c["start"], k["start"]))
            smaller = min(c["end"] - c["start"], k["end"] - k["start"])
            if smaller > 0 and inter / smaller >= 0.5:
                overlap = True
                break
        if not overlap:
            kept.append(c)
        if len(kept) >= top_n:
            break
    return kept


def save_highlights(highlights, out_path):
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(highlights, fh, indent=2)
    return out_path


def make_clips(input_path, highlights, out_dir, prefix="highlight", dry_run=False):
    """Cut each highlight into its own clip using the existing clip machinery."""
    os.makedirs(out_dir, exist_ok=True)
    outs = []
    for i, h in enumerate(highlights, 1):
        out = os.path.join(out_dir, f"{prefix}-{i:02d}.mp4")
        argv = vff.build_clip(input_path, out, h["start"],
                              round(h["end"] - h["start"], 2), strict=not dry_run)
        vff.run_cmd(argv, dry_run=dry_run)
        outs.append(out)
    return outs
