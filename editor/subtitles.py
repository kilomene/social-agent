"""Subtitles: SRT read/write/validate, burn-in builders, animated caption styles.

Transcription: `whisper`/`faster-whisper` are NOT installed in this environment,
so `transcribe` works from a user-supplied transcript file + a timing heuristic
(even word distribution across the speech portion of the audio, refined by the
silence map from `editor watch`). The whisper install path is documented in
editor/WORKFLOW.md — when whisper exists, use it instead; it is strictly
better than the heuristic.
"""

import json
import os
import re
import shutil

from video import ffmpeg as vff

MAX_LINE_CHARS = 42       # readability ceiling per line
MIN_CPS, MAX_CPS = 8, 25  # chars-per-second readable band


def _ts_to_s(ts):
    m = re.match(r"(\d+):(\d\d):(\d\d)[,.](\d\d\d)", ts.strip())
    if not m:
        raise ValueError(f"bad timestamp {ts!r}")
    h, mi, s, ms = map(int, m.groups())
    return h * 3600 + mi * 60 + s + ms / 1000


def _s_to_ts(sec):
    ms = int(round(sec * 1000))
    return f"{ms//3600000:02d}:{(ms//60000)%60:02d}:{(ms//1000)%60:02d},{ms%1000:03d}"


def parse_srt(path):
    """Parse SRT -> [{"n", "start", "end", "text"}]."""
    with open(path, encoding="utf-8") as fh:
        raw = fh.read().strip()
    cues, blocks = [], re.split(r"\n\s*\n", raw)
    for b in blocks:
        lines = [l for l in b.strip().splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        start = 0
        if re.match(r"\d+$", lines[0]) and "-->" in lines[1]:
            n, start = int(lines[0]), 1
        else:
            n = len(cues) + 1
        if "-->" not in lines[start]:
            continue
        s, e = [t.strip() for t in lines[start].split("-->")]
        text = "\n".join(lines[start + 1:])
        cues.append({"n": n, "start": _ts_to_s(s), "end": _ts_to_s(e), "text": text})
    return cues


def write_srt(cues, path):
    with open(path, "w", encoding="utf-8") as fh:
        for i, c in enumerate(cues, 1):
            fh.write(f"{i}\n{_s_to_ts(c['start'])} --> {_s_to_ts(c['end'])}\n"
                     f"{c['text'].strip()}\n\n")
    return path


def validate(cues):
    """Return [issue strings]: overlaps, too-long lines, unreadable speed."""
    issues = []
    prev_end = 0
    for c in cues:
        if c["start"] < prev_end - 0.001:
            issues.append(f"cue {c['n']}: overlaps previous cue")
        prev_end = c["end"]
        dur = max(0.1, c["end"] - c["start"])
        for line in c["text"].splitlines():
            if len(line) > MAX_LINE_CHARS:
                issues.append(f"cue {c['n']}: line too long ({len(line)} chars)")
        cps = len(c["text"].replace("\n", " ")) / dur
        if cps > MAX_CPS:
            issues.append(f"cue {c['n']}: too fast to read ({cps:.0f} chars/sec)")
        if c["end"] <= c["start"]:
            issues.append(f"cue {c['n']}: zero/negative duration")
    return issues


def build_burn_in(input_path, output_path, srt_path, style="pop", strict=True):
    """Burn captions into the video with libass. Styles: pop, karaoke, minimal."""
    if strict and not os.path.exists(input_path):
        raise FileNotFoundError(f"input not found: {input_path!r}")
    if strict and not os.path.exists(srt_path):
        raise FileNotFoundError(f"srt not found: {srt_path!r}")
    if os.path.abspath(input_path) == os.path.abspath(output_path):
        raise ValueError("refusing: output would overwrite the input")
    ass_path = srt_path  # libass reads .srt directly
    force_style = {
        "pop": "FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,"
               "OutlineColour=&H80000000,BorderStyle=1,Outline=2,Shadow=1,"
               "Alignment=2,MarginV=60",
        "karaoke": "FontName=Arial,FontSize=24,PrimaryColour=&H0000FFFF,"
                   "SecondaryColour=&H00FFFFFF,OutlineColour=&H80000000,"
                   "BorderStyle=1,Outline=2,Alignment=2,MarginV=60",
        "minimal": "FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,"
                   "OutlineColour=&H00000000,BorderStyle=1,Outline=1,"
                   "Alignment=2,MarginV=40",
    }.get(style, "pop")
    vf = f"subtitles='{ass_path}':force_style='{force_style}'"
    return [vff.FFMPEG, "-y", "-i", input_path, "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "19",
            "-c:a", "copy", output_path]


def karaoke_ass(cues, words_per_cue=4):
    """Build an ASS string with word-by-word karaoke highlight (\\k tags)."""
    header = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
              "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, "
              "SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
              "BorderStyle, Outline, Shadow, Alignment, MarginV\n"
              "Style: Pop,Arial,64,&H0000FFFF,&H00FFFFFF,&H80000000,&H00000000,"
              "-1,0,1,3,1,2,120\n"
              "[Events]\nFormat: Layer, Start, End, Style, Text\n")
    events = []
    for c in cues:
        words = c["text"].replace("\n", " ").split()
        chunks = [" ".join(words[i:i + words_per_cue])
                  for i in range(0, len(words), words_per_cue)] or [c["text"]]
        span = (c["end"] - c["start"]) / max(1, len(chunks))
        for j, ch in enumerate(chunks):
            s = c["start"] + j * span
            e = min(c["end"], s + span)
            tagged = " ".join(f"{{\\k{int(span*100)}}}{w}" for w in ch.split())
            events.append(f"Dialogue: 0,{_s_to_ts(s)},{_s_to_ts(e)},Pop,{tagged}")
    return header + "\n".join(events) + "\n"


def heuristic_srt(transcript_path, duration, silence_spans, out_path,
                  words_per_cue=6):
    """Timing heuristic: distribute words evenly across speech (non-silent)
    regions. Honest fallback when whisper is unavailable."""
    with open(transcript_path, encoding="utf-8") as fh:
        words = fh.read().split()
    if not words:
        raise ValueError("transcript is empty")
    speech = []
    cursor = 0.0
    for s, e in sorted(silence_spans):
        if s > cursor:
            speech.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < duration:
        speech.append((cursor, duration))
    if not speech:
        speech = [(0, duration)]
    total_speech = sum(e - s for s, e in speech)
    per_word = total_speech / len(words)
    # linear walk: fill each speech region with cues of <= words_per_cue words
    cues, wi, ti, t = [], 0, 0, 0.0
    while wi < len(words) and ti < len(speech):
        s, e = speech[ti]
        t = max(t, s)
        chunk = words[wi:wi + words_per_cue]
        c_dur = len(chunk) * per_word
        if t + c_dur > e + 0.01:
            ti += 1
            continue
        cues.append({"start": round(t, 2), "end": round(t + c_dur, 2),
                     "text": " ".join(chunk)})
        t += c_dur
        wi += len(chunk)
    # any leftover words go in the final speech region
    if wi < len(words):
        s, e = speech[-1]
        cues.append({"start": round(max(t, s), 2), "end": round(e, 2),
                     "text": " ".join(words[wi:])})
    write_srt(cues, out_path)
    return out_path


def whisper_available():
    return shutil.which("whisper") is not None or shutil.which("faster-whisper") is not None
