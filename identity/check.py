"""Identity check: is this text written AS the account owner? (stdlib)

`check_identity(text, label, home)` -> {"pass", "reasons", "advisories"}.

Fail conditions (refused at the content gate):
  - identity-break phrases: claiming to be an AI/agent/chatbot/language
    model, "as an AI" disclaimers, robotic opinion disclaimers.
  - persona violations: phrases on the persona file's never-say list.

Advisories (warned, not refused):
  - no first-person voice detected (consider writing as the owner).
  - no persona file on file for the account (create one with
    `identity create`).

Personas live in <home>/identity/accounts/<label>.md with YAML front-matter:
  name, voice_traits (list), known_facts (list), opinions (list),
  never_say (list). Body = free-form persona notes.
"""

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from policy import yaml_lite

# Claiming to be an AI/agent/chatbot breaks embodiment. Always refused.
IDENTITY_BREAK_PATTERNS = [
    r"(?i)\bas an ai\b",
    r"(?i)\bi['’]m an ai\b",
    r"(?i)\bi am an ai\b",
    r"(?i)\bi['’]m a chatbot\b",
    r"(?i)\bi am a chatbot\b",
    r"(?i)\bi['’]m a language model\b",
    r"(?i)\bi am a language model\b",
    r"(?i)\bas a language model\b",
    r"(?i)\bas an artificial intelligence\b",
    r"(?i)\bi['’]m just an ai\b",
    r"(?i)\bmy training data\b",
    r"(?i)\bmy knowledge cutoff\b",
    r"(?i)\bi don['’]t have personal opinions\b",
    r"(?i)\bi cannot form opinions\b",
    r"(?i)\bi have no opinions\b",
    r"(?i)\ban ai like me\b",
]

_COMPILED = [re.compile(p) for p in IDENTITY_BREAK_PATTERNS]

_FIRST_PERSON = re.compile(r"(?i)\b(i|me|my|mine|we|us|our|ours)\b")


def persona_path(home, label):
    return os.path.join(home, "identity", "accounts", f"{label}.md")


def load_persona(home, label):
    """Return (meta dict, body str) or (None, '') if no persona file."""
    p = persona_path(home, label)
    if not os.path.exists(p):
        return None, ""
    with open(p, encoding="utf-8") as fh:
        raw = fh.read()
    meta, body = {}, raw
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            try:
                meta = yaml_lite.loads(raw[3:end]) or {}
            except Exception:
                meta = {}
            body = raw[end + 4:].strip()
    return meta, body


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    # yaml_lite doesn't parse flow-style lists; accept a JSON-ish "[a, b]"
    # string defensively so hand-written personas still work.
    s = str(v).strip()
    if s.startswith("[") and s.endswith("]"):
        try:
            import json
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return parsed
        except ValueError:
            pass
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [x.strip().strip('"\'') for x in inner.split(",")]
    return [v]


def check_identity(text, label, home):
    reasons, advisories = [], []
    meta, _ = load_persona(home, label)

    for rx in _COMPILED:
        m = rx.search(text or "")
        if m:
            reasons.append(f"identity break: {m.group(0)!r} — the agent must "
                           f"never claim to be an AI/agent/chatbot in outward content")

    if meta is not None:
        for phrase in _as_list(meta.get("never_say")):
            if phrase and phrase.lower() in (text or "").lower():
                reasons.append(f"persona violation: {phrase!r} is on "
                               f"{label}'s never-say list")
    else:
        advisories.append(f"no persona on file for account {label!r} — run "
                          f"`identity create --account {label}` to define the owner's voice")

    if not _FIRST_PERSON.search(text or ""):
        advisories.append("no first-person voice detected — write as the owner "
                          "(I/my/me), not as an observer")

    return {"pass": not reasons, "reasons": reasons, "advisories": advisories,
            "account": label}
