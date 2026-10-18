"""QC gates A/B/C/D as code. Never fabricates values.

Every check is {"name", "passed" (True/False), "evidence" (or None),
"detail"}. Missing evidence = fail with an explicit reason, never a
guessed pass. Visual-taste checks (watermarks, artifacts, identity match)
need a recorded review dict — the skill self-review pass (character-
consistency Step 4) captured as data, not vibes.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone

from . import definition as d
from . import script as script_mod
from .providers.base import sniff_image_kind

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

REALISM_FINAL_VALIDATION = [
    "looks like real live-action footage",
    "sounds like real humans (natural, not synthesized-flat)",
    "physics are believable",
    "character identity unchanged (or deliberately, explicably updated)",
    "each voice belongs to its correct character",
    "weather consistent with the established scene state",
    "objects (vehicles, props, locations) consistent",
    "camera behaves like a professional operator would",
    "music matches the scene's setting and emotion",
    "no visible AI artifacts",
]

PUBLISH_STATES = ("defined", "produced", "qc'd", "proposed",
                  "uploaded/scheduled", "owner-approved", "aired")

_AIR_DAYS = (6, 1, 4)  # Sunday, Tuesday, Friday
_AIR_TZ = "America/New_York"
_AIR_HOUR = 15


# --- verdict plumbing ---------------------------------------------------------
def make_check(name, passed, evidence=None, detail=""):
    return {"name": name, "passed": bool(passed),
            "evidence": evidence, "detail": detail or ""}


def verdict(checks):
    failed = [c["name"] for c in checks if not c["passed"]]
    unverified = [c["name"] for c in checks
                  if not c["passed"] and c["evidence"] is None]
    return {"passed": not failed, "checks": checks,
            "failed": failed, "unverified": unverified,
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


# --- shared evidence readers ---------------------------------------------------
def identity_block_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ffmpeg_bin():
    from video import ffmpeg as vff
    return vff.which_ffmpeg()


def probe_dims(path):
    """(width, height) or None when ffprobe/ffmpeg unavailable."""
    try:
        from video import ffmpeg as vff
        if not vff.ffprobe():
            return None
        info = vff.info(path)
        w, h = info.get("width"), info.get("height")
        return (int(w), int(h)) if w and h else None
    except Exception:
        return None


def probe_duration(path):
    try:
        from video import ffmpeg as vff
        if not vff.ffprobe():
            return None
        return float(vff.info(path).get("duration") or 0)
    except Exception:
        return None


def probe_vcodec(path):
    try:
        from video import ffmpeg as vff
        if not vff.ffprobe():
            return None
        return vff.info(path).get("vcodec")
    except Exception:
        return None


def motion_score(path, samples=10):
    """Max mean-abs frame delta over 1fps samples (64x64 gray).

    Returns float, or None when ffmpeg is unavailable (no evidence).
    A real moving clip scores well above ~3.0; a frozen still ~0."""
    ff = _ffmpeg_bin()
    if not ff:
        return None
    proc = subprocess.run(
        [ff, "-v", "error", "-i", path, "-vf",
         "fps=1,scale=64:64,format=gray", "-f", "rawvideo", "-frames:v",
         str(samples), "pipe:1"],
        capture_output=True)
    if proc.returncode != 0 or not proc.stdout:
        return None
    frame = 64 * 64
    n = len(proc.stdout) // frame
    if n < 2:
        return None
    import math
    best = 0.0
    prev = proc.stdout[:frame]
    for i in range(1, n):
        cur = proc.stdout[i * frame:(i + 1) * frame]
        diff = sum(abs(a - b) for a, b in zip(prev, cur)) / frame
        best = max(best, diff)
        prev = cur
    return round(best, 3)


def has_black_bars(path, thresh=8.0):
    """Detect letterbox/pillarbox: dark border rows/cols in the mid frame.

    Returns True/False, or None when ffmpeg is unavailable."""
    ff = _ffmpeg_bin()
    if not ff:
        return None
    dur = probe_duration(path) or 2.0
    proc = subprocess.run(
        [ff, "-v", "error", "-ss", str(dur / 2), "-i", path,
         "-vf", "scale=160:90,format=gray", "-f", "rawvideo",
         "-frames:v", "1", "pipe:1"],
        capture_output=True)
    if proc.returncode != 0 or len(proc.stdout) < 160 * 90:
        return None
    px = proc.stdout
    w, h = 160, 90
    rows = [[px[y * w + x] for x in range(w)] for y in range(h)]

    def mean(vals):
        return sum(vals) / len(vals)

    top = mean([v for y in range(4) for v in rows[y]])
    bottom = mean([v for y in range(h - 4, h) for v in rows[y]])
    left = mean([rows[y][x] for y in range(h) for x in range(4)])
    right = mean([rows[y][x] for y in range(h) for x in range(w - 4, w)])
    return (top < thresh and bottom < thresh) or \
           (left < thresh and right < thresh)


def audio_mean_db(path):
    """Mean volume dB via ffmpeg volumedetect; None when unavailable."""
    ff = _ffmpeg_bin()
    if not ff or not os.path.exists(path):
        return None
    proc = subprocess.run(
        [ff, "-v", "info", "-i", path, "-af", "volumedetect",
         "-f", "null", "-"],
        capture_output=True, text=True)
    m = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", proc.stderr)
    if m:
        return float(m.group(1))
    if "n/a" in proc.stderr and "mean_volume" in proc.stderr:
        return float("-inf")
    return None


# --- GATE A: pre-production -----------------------------------------------------
def load_voice_cast(project_dir):
    path = os.path.join(project_dir, "voice-cast.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_identity_blocks(project_dir):
    """{CHAR: {"text", "words", "hash"}} for identity-blocks/*.md."""
    out = {}
    idir = os.path.join(project_dir, "identity-blocks")
    if not os.path.isdir(idir):
        return out
    hashes = {}
    hp = os.path.join(idir, "hashes.json")
    if os.path.exists(hp):
        with open(hp, encoding="utf-8") as fh:
            hashes = json.load(fh)
    for fn in sorted(os.listdir(idir)):
        if not fn.endswith(".md"):
            continue
        char = os.path.splitext(fn)[0].upper()
        with open(os.path.join(idir, fn), encoding="utf-8") as fh:
            text = fh.read().strip()
        words = len(text.split())
        out[char] = {"text": text, "words": words,
                     "hash": identity_block_hash(text),
                     "recorded_hash": hashes.get(char)}
    return out


def portrait_files(project_dir, character):
    pdir = os.path.join(project_dir, "assets", "portraits", character)
    if not os.path.isdir(pdir):
        return []
    out = []
    for fn in sorted(os.listdir(pdir)):
        p = os.path.join(pdir, fn)
        if not os.path.isfile(p):
            continue
        with open(p, "rb") as fh:
            head = fh.read(32)
        if sniff_image_kind(head):
            out.append(p)
    return out


def character_in_bible(bible_text, character):
    canon = script_mod.canonical_character(character)
    for variant in {canon, character.upper()}:
        if re.search(r"\*\*" + re.escape(variant) + r"\b", bible_text,
                     re.IGNORECASE):
            return True
    return False


def gate_a(project_dir, parsed_script, episode_no=1):
    """Pre-production gate. parsed_script = script.parse_script() output."""
    checks = []
    bible_path = os.path.join(project_dir, "CHARACTER-BIBLE.md")
    bible = ""
    if os.path.exists(bible_path):
        with open(bible_path, encoding="utf-8") as fh:
            bible = fh.read()
    checks.append(make_check(
        "character_bible_exists", bool(bible.strip()),
        evidence=bible_path if bible else None,
        detail="" if bible else "CHARACTER-BIBLE.md missing or empty"))

    speakers = script_mod.speaking_characters(parsed_script)
    checks.append(make_check(
        "dialogue_inventory_parsed", bool(parsed_script["dialogue"]),
        evidence={"scenes": len(parsed_script["scenes"]),
                  "lines": len(parsed_script["dialogue"]),
                  "speakers": speakers},
        detail="" if parsed_script["dialogue"]
        else "no dialogue lines parsed from script"))

    uncovered = [c for c in speakers if not character_in_bible(bible, c)]
    checks.append(make_check(
        "bible_covers_every_speaker", not uncovered and bool(speakers),
        evidence={"speakers": speakers, "uncovered": uncovered},
        detail=("speakers missing from bible: " + ", ".join(uncovered))
        if uncovered else ""))

    cast = load_voice_cast(project_dir)
    uncast = [c for c in speakers
              if not (cast.get(c) or {}).get("voice_id")]
    unlocked = [c for c in speakers
                if (cast.get(c) or {}).get("voice_id")
                and not (cast.get(c) or {}).get("locked")]
    checks.append(make_check(
        "voice_cast_locked", not uncast and not unlocked and bool(speakers),
        evidence={"cast": {c: (cast.get(c) or {}).get("voice_id")
                           for c in speakers},
                  "uncast": uncast, "unlocked": unlocked},
        detail=("missing locked voice IDs: "
                + ", ".join(sorted(set(uncast + unlocked)))) if (uncast or unlocked)
        else ""))

    blocks = load_identity_blocks(project_dir)
    block_problems = []
    for c in speakers:
        b = blocks.get(c)
        if not b:
            block_problems.append(f"{c}: no identity-blocks/{c}.md")
        elif not (100 <= b["words"] <= 150):
            block_problems.append(
                f"{c}: identity block {b['words']} words (need 100-150)")
        elif b["recorded_hash"] and b["recorded_hash"] != b["hash"]:
            block_problems.append(f"{c}: hash mismatch vs hashes.json")
    checks.append(make_check(
        "identity_blocks_verbatim", not block_problems and bool(speakers),
        evidence={c: {"words": blocks[c]["words"], "hash": blocks[c]["hash"]}
                  for c in speakers if c in blocks},
        detail="; ".join(block_problems)))

    portrait_problems = [c for c in speakers
                         if not portrait_files(project_dir, c)]
    checks.append(make_check(
        "master_portraits_verified", not portrait_problems and bool(speakers),
        evidence={c: portrait_files(project_dir, c) for c in speakers},
        detail=("no verified master portrait: " + ", ".join(portrait_problems))
        if portrait_problems else ""))

    ledger = os.path.join(project_dir, "continuity", "ledger.md")
    ledger_ok = os.path.exists(ledger) and os.path.getsize(ledger) > 0
    checks.append(make_check(
        "continuity_ledger_read", ledger_ok,
        evidence={"path": ledger,
                  "size": os.path.getsize(ledger) if os.path.exists(ledger)
                  else 0} if ledger_ok else None,
        detail="" if ledger_ok
        else "continuity/ledger.md missing or empty — read it before scripting"))

    return verdict(checks)


# --- GATE B: per-shot -------------------------------------------------------------
def gate_b_shot(clip_path, expected_identity_hash, actual_identity_hash,
                core_look_present, review=None):
    """Per-shot verdict. review = recorded self-review dict, e.g.
    {"watermark_free": True, "artifacts": "none", "identity_match": True,
     "reviewer": "host", "at": "..."} — explicit evidence, never assumed."""
    review = review or {}
    checks = []

    checks.append(make_check(
        "identity_block_hash_match",
        bool(expected_identity_hash) and
        expected_identity_hash == actual_identity_hash,
        evidence={"expected": expected_identity_hash,
                  "actual": actual_identity_hash},
        detail="" if expected_identity_hash == actual_identity_hash
        else "generation record identity hash does not match the verbatim "
             "identity block — regenerate with the block pasted verbatim"))

    checks.append(make_check(
        "core_look_block_present", bool(core_look_present),
        evidence={"core_look_present": bool(core_look_present)},
        detail="" if core_look_present
        else "generation record lacks the Core Look block "
             "(cinematic-effect-engine) — regenerate with it"))

    exists = bool(clip_path) and os.path.exists(clip_path or "")
    dims = probe_dims(clip_path) if exists else None
    ratio_ok = (dims is not None and dims[1] > 0
                and abs(dims[0] / dims[1] - 16 / 9) < 0.02)
    checks.append(make_check(
        "real_video_file", exists,
        evidence={"path": clip_path} if exists else None,
        detail="" if exists else
        "clip missing — blocked/region-gated counts as FAIL, never pass"))

    score = motion_score(clip_path) if exists else None
    checks.append(make_check(
        "real_video_motion", score is not None and score >= 3.0,
        evidence={"motion_score": score} if score is not None else None,
        detail="" if (score is not None and score >= 3.0)
        else ("no frame-delta evidence (ffmpeg missing?) — FAIL"
              if score is None
              else f"frozen/still detected (motion score {score}) — "
                   "no still images EVER; regenerate as real video")))

    bars = has_black_bars(clip_path) if exists else None
    checks.append(make_check(
        "edge_to_edge_16x9",
        ratio_ok and bars is False,
        evidence={"dims": dims, "ratio_ok": ratio_ok,
                  "black_bars": bars} if exists else None,
        detail="" if (ratio_ok and bars is False)
        else ("no probe evidence (ffmpeg missing?) — FAIL"
              if dims is None or bars is None
              else f"not edge-to-edge 16:9 (dims={dims}, bars={bars}) — "
                   "pillarbox/letterbox forbidden")))

    wm = review.get("watermark_free")
    checks.append(make_check(
        "no_inframe_watermark_text", wm is True,
        evidence={"review": review} if review else None,
        detail="" if wm is True
        else "no watermark/text review evidence — record a self-review "
             "(character-consistency Step 4) or reject the shot"))

    ident = review.get("identity_match")
    checks.append(make_check(
        "identity_self_review", ident is True,
        evidence={"review": review} if review else None,
        detail="" if ident is True
        else "no identity self-review evidence — compare the clip to the "
             "bible and record the verdict"))

    art = (review.get("artifacts") or "").strip().lower()
    checks.append(make_check(
        "no_visible_artifacts", art in ("none", "no", "clean", "pass"),
        evidence={"review": review} if review else None,
        detail="" if art in ("none", "no", "clean", "pass")
        else "no artifact review evidence — check for plastic skin, warped "
             "hands/faces, morphing (cinematic invisibility)"))

    v = verdict(checks)
    if not v["passed"]:
        reasons = "; ".join(
            f"{c['name']}: {c['detail']}" for c in checks if not c["passed"])
        v["corrective"] = ("REGENERATE THIS SHOT ALONE with: " + reasons
                           + ". Preserve every other accepted shot.")
    return v


# --- GATE C: assembly ---------------------------------------------------------------
def gate_c(spec):
    """spec: {"master_path", "dialogue" (inventory), "episode_no",
    "voice_cast" ({CHAR: {"voice_id", "locked"}}), "voice_dir",
    "mix_manifest" (dict), "assembly_argv" (list), "lipsync_report" (dict),
    "score" ({"path", "ducked": bool}), "srt_path",
    "dialogue_windows" ([{"index","start_s","end_s"}]) }."""
    checks = []
    master = spec.get("master_path")
    dur = probe_duration(master) if master and os.path.exists(master) else None
    runtime_ok = dur is not None and 5 * 60 <= dur <= 10 * 60
    checks.append(make_check(
        "runtime_5_to_10_min", runtime_ok,
        evidence={"duration_s": dur} if dur is not None else None,
        detail="" if runtime_ok
        else ("no duration evidence (ffprobe missing?) — FAIL"
              if dur is None
              else f"runtime {dur:.1f}s outside 5-10 min")))

    dialogue = spec.get("dialogue") or []
    voice_dir = spec.get("voice_dir") or ""
    cast = spec.get("voice_cast") or {}
    ep_no = spec.get("episode_no", 1)
    missing_tts, wrong_voice = [], []
    for line in dialogue:
        char = line["character"]
        vid = (cast.get(char) or {}).get("voice_id", "")
        fname = script_mod.voice_filename(
            ep_no, line["scene_no"], line["scene_dialogue_no"], char,
            vid or "UNKNOWN")
        fpath = os.path.join(voice_dir, fname)
        if not vid:
            wrong_voice.append(f"line {line['index']}: no locked voice for {char}")
        elif not os.path.exists(fpath):
            missing_tts.append(fname)
    checks.append(make_check(
        "every_line_has_locked_tts",
        not missing_tts and not wrong_voice and bool(dialogue),
        evidence={"missing": missing_tts[:10], "unvoiced": wrong_voice[:10],
                  "lines": len(dialogue)},
        detail=("; ".join(wrong_voice[:5] + missing_tts[:5]))))

    manifest = spec.get("mix_manifest") or {}
    scenes = {d["scene_no"] for d in dialogue}
    man_scenes = (manifest.get("scenes") or {})
    man_problems = []
    null_layers = []
    for s in sorted(scenes):
        layers = man_scenes.get(s)
        if not layers:
            man_problems.append(f"scene {s}: missing from mix manifest")
            continue
        for layer in ("dialogue", "foley", "environment", "music"):
            if layer not in layers:
                man_problems.append(f"scene {s}: layer {layer!r} missing")
            elif layers[layer] is None:
                null_layers.append(f"scene {s}/{layer}")
        if layers.get("dialogue") is None and any(
                d["scene_no"] == s for d in dialogue):
            man_problems.append(f"scene {s}: has dialogue but null mix layer")
    checks.append(make_check(
        "four_layer_mix_manifest", not man_problems,
        evidence={"manifest_scenes": sorted(man_scenes),
                  "explicit_null_layers": null_layers},
        detail="; ".join(man_problems)))

    silent = []
    no_evidence = []
    for line in dialogue:
        char = line["character"]
        vid = (cast.get(char) or {}).get("voice_id", "")
        if not vid:
            continue
        fpath = os.path.join(voice_dir, script_mod.voice_filename(
            ep_no, line["scene_no"], line["scene_dialogue_no"], char, vid))
        if not os.path.exists(fpath):
            continue
        db = audio_mean_db(fpath)
        if db is None:
            no_evidence.append(line["index"])
        elif db <= -60:
            silent.append(line["index"])
    energy_ok = not silent and not no_evidence and bool(dialogue)
    checks.append(make_check(
        "audio_energy_per_dialogue_window", energy_ok,
        evidence={"silent_lines": silent,
                  "no_evidence_lines": no_evidence} or None,
        detail="" if energy_ok
        else ("no audio evidence (ffmpeg missing?) — FAIL"
              if no_evidence and not silent
              else f"silent dialogue lines: {silent[:10]}")))

    argv = spec.get("assembly_argv") or []
    # The AGENTS.md mux gotcha: never let ffmpeg's default stream selection
    # pick a clip's native audio. Accept the two honest explicit forms:
    # a final A/V mux ("-map 0:v:0 -map 1:a:0") or a concat filter build
    # ("-map [outv] -map [outa]").
    map_ok = ("-map" in argv
              and (("0:v:0" in argv and "1:a:0" in argv)
                   or ("[outv]" in argv and "[outa]" in argv)))
    form = ("mux 0:v:0/1:a:0" if ("0:v:0" in argv and "1:a:0" in argv)
            else "concat [outv]/[outa]" if map_ok else "none")
    checks.append(make_check(
        "explicit_ffmpeg_map", map_ok,
        evidence={"map_form": form, "argv_tail": argv[-12:] if argv else []},
        detail="" if map_ok
        else "assembly did not record explicit stream mapping — ffmpeg "
             "default stream selection is forbidden (silent wrong-audio "
             "pick); use '-map 0:v:0 -map 1:a:0' (mux) or explicit "
             "filter-output maps (concat)"))

    report = spec.get("lipsync_report") or {}
    uncovered = [d["index"] for d in dialogue
                 if str(d["index"]) not in report and d["index"] not in report]
    gaps = [k for k, r in report.items()
            if isinstance(r, dict) and r.get("verdict") == "gap"]
    checks.append(make_check(
        "lipsync_verdict_per_line", not uncovered and bool(dialogue),
        evidence={"covered": len(report), "lines": len(dialogue),
                  "flagged_gaps": gaps},
        detail=("lines without lip-sync verdict: "
                + ", ".join(map(str, uncovered[:10]))) if uncovered else ""))

    score = spec.get("score") or {}
    score_dur = probe_duration(score["path"]) \
        if score.get("path") and os.path.exists(score["path"]) else None
    score_ok = (score_dur is not None and dur is not None
                and abs(score_dur - dur) / dur < 0.05
                and bool(score.get("ducked")))
    checks.append(make_check(
        "full_length_score_ducked", score_ok,
        evidence={"score_duration_s": score_dur,
                  "ducked": bool(score.get("ducked"))}
        if score_dur is not None else None,
        detail="" if score_ok
        else "need a full-length original score, ducked under dialogue "
             "(no copyrighted music, never silent)"))

    srt_path = spec.get("srt_path")
    cap_problems = []
    coverage = None
    if not srt_path or not os.path.exists(srt_path):
        cap_problems.append("captions srt missing")
    else:
        try:
            from editor import subtitles as subs_mod
            cues = subs_mod.parse_srt(srt_path)
            issues = subs_mod.validate(cues)
            cap_problems.extend(f"subtitle: {i}" for i in issues)
            windows = spec.get("dialogue_windows") or []
            if not windows:
                cap_problems.append("no dialogue_windows timing — "
                                    "coverage unverifiable")
            else:
                def to_s(ts):
                    h, m, rest = ts.split(":")
                    s = rest.split(",")
                    return (int(h) * 3600 + int(m) * 60 + int(s[0])
                            + int(s[1]) / 1000)
                uncovered_w = []
                for wline in windows:
                    if not any(to_s(c["start"]) <= wline["start_s"] and
                               to_s(c["end"]) >= wline["end_s"]
                               for c in cues):
                        uncovered_w.append(wline["index"])
                coverage = {"windows": len(windows),
                            "uncovered": uncovered_w}
                if uncovered_w:
                    cap_problems.append(
                        "dialogue windows without caption coverage: "
                        + ", ".join(map(str, uncovered_w[:10])))
        except Exception as exc:
            cap_problems.append(f"caption check error: {exc}")
    checks.append(make_check(
        "captions_cover_all_dialogue", not cap_problems,
        evidence=coverage,
        detail="; ".join(cap_problems)))

    qa_detail, qa_evidence = "", None
    if master and os.path.exists(master):
        try:
            from editor import qa as qa_mod
            res = qa_mod.verify(master, srt_path if srt_path and
                                os.path.exists(srt_path or "") else None)
            qa_evidence = res.get("details")
            if not res["passed"]:
                qa_detail = "; ".join(res["issues"])
        except Exception as exc:
            qa_detail = f"qa verify error: {exc}"
    else:
        qa_detail = "master missing — cannot verify"
    checks.append(make_check(
        "no_black_frames_or_corrupt_audio", not qa_detail,
        evidence=qa_evidence, detail=qa_detail))

    v = verdict(checks)
    v["flagged_lipsync_gaps"] = gaps
    return v


# --- GATE D: pre-publish ------------------------------------------------------------
def next_air_slot(now=None):
    """Next Sun/Tue/Fri 3:00 PM America/New_York (DST-aware)."""
    if ZoneInfo is None:
        raise d.PipelineError("zoneinfo unavailable — cannot compute air slot")
    tz = ZoneInfo(_AIR_TZ)
    now = now or datetime.now(tz)
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    for delta in range(0, 8):
        day = now + timedelta(days=delta)
        if day.weekday() in _AIR_DAYS:
            slot = day.replace(hour=_AIR_HOUR, minute=0, second=0,
                               microsecond=0)
            if slot > now:
                return slot
    raise d.PipelineError("no air slot found in 8 days")  # pragma: no cover


def gate_d(spec):
    """spec: {"master_path", "teaser" ({"path","watermark_record"}),
    "episode_cut" ({"path","overlay_record"}), "realism_record"
    ({"items": {name: bool}, "reviewer", "at"}), "metadata" (dict),
    "publish_state" (str)}."""
    checks = []
    master = spec.get("master_path")
    dims = probe_dims(master) if master and os.path.exists(master) else None
    vcodec = probe_vcodec(master) if master and os.path.exists(master) else None
    master_ok = dims == (3840, 2160) and (vcodec or "").lower().startswith("vp9")
    checks.append(make_check(
        "master_3840x2160_vp9", master_ok,
        evidence={"dims": dims, "vcodec": vcodec} if dims else None,
        detail="" if master_ok
        else ("no probe evidence (ffprobe missing?) — FAIL"
              if dims is None
              else f"master is {dims} {vcodec}, need exactly 3840x2160 VP9")))

    teaser = spec.get("teaser") or {}
    wm = teaser.get("watermark_record") or {}
    wm_ok = (bool(teaser.get("path")) and os.path.exists(teaser["path"])
             and wm.get("kind") == "tiktok_teaser_watermark"
             and wm.get("position") == "bottom-right"
             and wm.get("animated") is True
             and "Nova Automation" in str(wm.get("text", ""))
             and wm.get("icon") == "youtube_play")
    checks.append(make_check(
        "tiktok_teaser_watermark", wm_ok,
        evidence={"watermark_record": wm} if wm else None,
        detail="" if wm_ok
        else "teaser needs the bottom-right ANIMATED watermark (YouTube play "
             "icon + 'Nova Automation', slide-in/out) — record required"))

    cut = spec.get("episode_cut") or {}
    ov = cut.get("overlay_record") or {}
    ov_ok = (bool(cut.get("path")) and os.path.exists(cut["path"])
             and ov.get("kind") == "youtube_episode_overlay"
             and ov.get("position") == "bottom-right"
             and ov.get("animated") is True
             and set(ov.get("elements") or []) >=
             {"like", "subscribe", "bell"})
    checks.append(make_check(
        "youtube_episode_overlay", ov_ok,
        evidence={"overlay_record": ov} if ov else None,
        detail="" if ov_ok
        else "episode cut needs the bottom-right animated like/subscribe/bell "
             "overlay — record required"))

    rec = spec.get("realism_record") or {}
    items = rec.get("items") or {}
    missing_items = [name for name in REALISM_FINAL_VALIDATION
                     if name not in items]
    failed_items = [name for name, ok in items.items() if not ok]
    realism_ok = (not missing_items and not failed_items
                  and len(items) == len(REALISM_FINAL_VALIDATION))
    checks.append(make_check(
        "realism_final_validation_all_pass", realism_ok,
        evidence={"items": items, "reviewer": rec.get("reviewer"),
                  "at": rec.get("at")} if rec else None,
        detail="" if realism_ok
        else ("10-item REALISM Final Validation record missing — "
              "all-pass record required"
              if not rec
              else "failing/missing items: "
              + ", ".join(missing_items + failed_items))))

    meta = spec.get("metadata") or {}
    meta_problems = []
    for key in ("title", "description", "thumbnail_brief"):
        if not str(meta.get(key) or "").strip():
            meta_problems.append(f"metadata.{key} missing")
    if meta.get("audience") != "NOT made for kids":
        meta_problems.append("audience must be 'NOT made for kids'")
    if meta.get("channel") != "Nova Automation":
        meta_problems.append("channel must be 'Nova Automation'")
    checks.append(make_check(
        "metadata_package", not meta_problems,
        evidence={"metadata": meta} if meta else None,
        detail="; ".join(meta_problems)))

    try:
        slot = next_air_slot()
        slot_ok, slot_ev = True, {"next_slot": slot.isoformat()}
        slot_detail = ""
    except d.PipelineError as exc:
        slot_ok, slot_ev, slot_detail = False, None, str(exc)
    checks.append(make_check("air_slot_scheduled", slot_ok,
                             evidence=slot_ev, detail=slot_detail))

    state = spec.get("publish_state", "defined")
    checks.append(make_check(
        "human_approval_state_machine",
        state in ("qc'd",),
        evidence={"publish_state": state,
                  "states": list(PUBLISH_STATES)},
        detail="" if state in ("qc'd",)
        else (f"publish_state is {state!r}: a publish proposal is only valid "
              "from \"qc'd\"; human approval then flows produced -> QC'd -> "
              "uploaded/scheduled -> owner-approved -> aired via the "
              "approvals queue + host browser — never auto-published")))

    return verdict(checks)


def advance_publish_state(current, to):
    """Validate the human-gated publish state machine."""
    order = list(PUBLISH_STATES)
    if current not in order or to not in order:
        raise d.PipelineError(f"bad publish state {current!r} -> {to!r}")
    if current == to:
        return to  # idempotent: node retries must not crash on re-advance
    if order.index(to) != order.index(current) + 1:
        raise d.PipelineError(
            f"illegal publish transition {current!r} -> {to!r}; "
            f"must advance one step: {' -> '.join(order)}")
    return to
