"""Style gate: every outbound DM reply passes through here.

Enforces the owner's style rules VERBATIM:
- Never use em dashes (—) or en dashes with spaces (–) as punctuation.
- Use periods, commas, or "and"/"but" to connect thoughts instead.
- Write short, plain sentences, like a real person texting quickly.
- No "I hope this helps," no "certainly," no overly polished phrasing.
- Contractions are fine (don't, can't, it's).
- If a sentence would use an em dash, just split it into two sentences.

The gate REWRITES — it never silently drops a reply. If every sentence is
stripped by the banned-phrase filter, a neutral "Got it." is returned so the
reply still goes out (marked, never empty).
"""

import re

# Phrases that never reach a correspondent. Matched case-insensitively;
# the whole sentence carrying one is dropped (see gate()).
BANNED_PHRASES = (
    "i hope this helps",
    "certainly",
    "as an ai",
    "as a language model",
    "i am an ai",
    "i'm an ai",
)

# A sentence longer than this gets split at a natural joint so replies read
# like fast texting, not paragraphs.
MAX_WORDS = 24

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WS = re.compile(r"\s+")
_EM_DASH = re.compile(r"\s*—\s*")
_SPACED_EN_DASH = re.compile(r"\s+–\s+")


def _cap_first(s):
    for i, ch in enumerate(s):
        if ch.isalpha():
            return s[:i] + ch.upper() + s[i + 1:]
    return s


def _strip_banned(sentence):
    """Return the sentence with banned phrases removed, or None if the
    sentence was nothing but banned phrasing."""
    removed = False
    low = sentence.lower()
    for phrase in BANNED_PHRASES:
        if phrase in low:
            # Remove the phrase plus a trailing comma/space it owned.
            pat = re.compile(re.escape(phrase) + r"\s*,?\s*", re.I)
            sentence = pat.sub("", sentence).strip()
            low = sentence.lower()
            removed = True
    if removed:
        # Leftover fragments like "!" or "and" alone are not sentences.
        words = re.findall(r"[A-Za-z0-9']+", sentence)
        if len(words) <= 1:
            return None
    return sentence


def _split_long(sentence):
    """Split an over-long sentence at the first natural joint."""
    words = sentence.split()
    if len(words) <= MAX_WORDS:
        return [sentence]
    for joint in (", and ", ", but ", "; ", ", so ", ", or "):
        idx = sentence.find(joint)
        if idx != -1:
            first = sentence[:idx].rstrip(",;") + "."
            second = _cap_first(sentence[idx + len(joint):].lstrip())
            rest = _split_long(second)
            return [first] + rest
    return [sentence]


def gate(text):
    """Rewrite text to the owner's DM style. Always returns non-empty."""
    text = _WS.sub(" ", (text or "").strip())
    if not text:
        return "Got it."
    # Em dash: split into two sentences (capitalize the second half).
    parts = []
    for chunk in _EM_DASH.split(text):
        parts.append(chunk)
    text = ""
    for i, chunk in enumerate(parts):
        chunk = chunk.strip()
        if not chunk:
            continue
        if i > 0:
            chunk = _cap_first(chunk)
            text = text.rstrip()
            if text and text[-1] not in ".!?":
                text += "."
            text += " " + chunk
        else:
            text = chunk
    # Spaced en dash -> comma; any remaining en dash -> hyphen.
    text = _SPACED_EN_DASH.sub(", ", text).replace("–", "-")
    # Sentence pass: drop banned-phrase sentences, split long ones.
    out = []
    for sent in _SENT_SPLIT.split(text):
        sent = sent.strip(" ,;")
        if not sent:
            continue
        kept = _strip_banned(sent)
        if kept is None:
            continue
        out.extend(_split_long(kept))
    # Rewrites, never silent drops.
    if not out:
        return "Got it."
    result = " ".join(out)
    result = _WS.sub(" ", result).strip()
    return result or "Got it."
