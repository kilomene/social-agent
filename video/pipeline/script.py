"""Markdown screenplay parser (Mirror Lake artifact formats).

Scene headers:    **SCENE N — EXT./INT. LOCATION — TIME**
Dialogue lines:   CHARACTER: line        (parentheticals, (V.O.) flags kept)
Stage directions: *italic action lines*  (ignored for the dialogue inventory)

Produces the dialogue inventory GATE A/C/D consume, plus the deterministic
voice-file naming: voice-audio/e<NN>-s<scene>d<dialogue#>_<character>-<voiceid>.wav
"""

from __future__ import annotations

import os
import re

_SCENE_RE = re.compile(
    r"^\*\*SCENE\s+(\d+)\s*[—–-]\s*(EXT\.|INT\.|EXT/INT\.)\s*(.+?)\s*[—–-]\s*(.+?)\*\*$")
_DIALOGUE_RE = re.compile(
    r"^([A-Z][A-Z .'\-]+?)\s*:\s*(.+)$")
_VO_RE = re.compile(r"\(V\.?O\.?\)", re.IGNORECASE)
_PAREN_RE = re.compile(r"^\(([^)]*)\)\s*")
_ACT_RE = re.compile(r"^#{1,3}\s*(COLD OPEN|ACT [A-Z]+|EPILOGUE|PROLOGUE)", re.IGNORECASE)


def canonical_character(name):
    """MAYA OKORO -> MAYA; handles 'MS. HART' -> MS. HART."""
    name = name.strip().upper()
    name = re.sub(r"\s*\(.*?\)\s*", "", name)  # drop "(16)" style notes
    parts = name.split()
    if len(parts) >= 2 and len(parts[0]) > 2 and not parts[0].endswith("."):
        return parts[0]
    return name


def voice_filename(episode_no, scene_no, dialogue_no, character, voice_id):
    char = re.sub(r"[^A-Za-z0-9]+", "", canonical_character(character)).upper()
    vid = re.sub(r"[^A-Za-z0-9\-_]+", "", str(voice_id))
    return (f"voice-audio/e{int(episode_no):02d}-s{int(scene_no)}"
            f"d{int(dialogue_no)}_{char}-{vid}.wav")


def parse_script(text):
    """Parse a screenplay markdown file -> {"scenes": [...], "dialogue": [...]}.

    scenes: [{no, int_ext, location, time, act, heading, body}]
    dialogue: [{index, scene_no, scene_dialogue_no, character, line, vo,
               parenthetical}]
    """
    scenes, dialogue = [], []
    current = None
    act = ""
    global_idx = 0
    scene_dlg_no = 0

    def close_scene():
        nonlocal current
        if current is not None:
            scenes.append(current)
            current = None

    for raw in text.splitlines():
        line = raw.strip()
        m = _ACT_RE.match(line)
        if m:
            act = m.group(1).upper()
            continue
        m = _SCENE_RE.match(line)
        if m:
            close_scene()
            no, int_ext, location, time = m.groups()
            current = {"no": int(no), "int_ext": int_ext,
                       "location": location.strip(), "time": time.strip(),
                       "act": act, "heading": line.strip("*"), "body": [],
                       "dialogue_nos": []}
            scene_dlg_no = 0
            continue
        if current is None:
            continue
        if not line:
            continue
        m = _DIALOGUE_RE.match(line)
        if m and len(m.group(1).strip()) <= 30:
            name, spoken = m.group(1).strip(), m.group(2).strip()
            vo = bool(_VO_RE.search(line))
            paren = ""
            pm = _PAREN_RE.match(spoken)
            if pm:
                paren = pm.group(1)
                spoken = spoken[pm.end():].strip()
            global_idx += 1
            scene_dlg_no += 1
            entry = {"index": global_idx, "scene_no": current["no"],
                     "scene_dialogue_no": scene_dlg_no,
                     "character": canonical_character(name),
                     "raw_character": name, "line": spoken, "vo": vo,
                     "parenthetical": paren}
            dialogue.append(entry)
            current["dialogue_nos"].append(global_idx)
            current["body"].append(line)
        else:
            current["body"].append(line)
    close_scene()
    for s in scenes:
        s["body"] = "\n".join(s["body"])
    return {"scenes": scenes, "dialogue": dialogue}


def parse_script_file(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"script not found: {path!r}")
    with open(path, encoding="utf-8") as fh:
        return parse_script(fh.read())


def speaking_characters(parsed):
    """Ordered unique canonical character names with at least one line."""
    seen, out = set(), []
    for d in parsed["dialogue"]:
        if d["character"] not in seen:
            seen.add(d["character"])
            out.append(d["character"])
    return out


def dialogue_inventory(parsed):
    """Flat dialogue inventory for QC gates."""
    return list(parsed["dialogue"])
