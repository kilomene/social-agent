"""Reply drafting for DM agents.

Rules (from the owner's spec):
- Respond within one polling cycle of detecting a new message. No batching.
- Default: text reply.
- Voice note / image / video ONLY when the correspondent explicitly asks.
  The repo has no TTS and no image/video generation (voice/ is a style
  checker, audio/ is ffmpeg editing), so a media request gets an honest
  plain-language fallback INSIDE the reply text — never silence.
- If a request can't be fulfilled, say so plainly instead of going silent.

Drafts are templates + intent classification, style-gated later by
dm_agents.style.gate, and run through the repo's content gates (secrets,
identity, voice-human) before they are queued. Anything the gates refuse
falls back to a safe generic draft — a bad draft never reaches a human
unmarked.
"""

import re

from . import style as style_mod

# ---- media request detection (explicit asks only) ----
VOICE_PAT = re.compile(
    r"voice\s*(note|message|memo)|send\s+(me\s+)?(an?\s+)?audio|"
    r"audio\s*message|say\s+it\s+out\s+loud", re.I)
IMAGE_PAT = re.compile(
    r"send\s+(me\s+)?(a\s+|an\s+)?(pic|picture|photo|image|screenshot)",
    re.I)
VIDEO_PAT = re.compile(
    r"send\s+(me\s+)?(a\s+)?video|video\s+of\s+me|film\s+it", re.I)

QUESTION_PAT = re.compile(
    r"^(who|what|when|where|why|how|is|are|do|does|did|can|could|would|"
    r"should|will|have|has)\b", re.I)
GREETING_PAT = re.compile(
    r"^(hi|hey|hello|yo|sup|good\s*(morning|afternoon|evening|day))\b[!. ]*$",
    re.I)
THANKS_PAT = re.compile(r"\b(thank|thanks|thx|appreciated?|grateful)\b", re.I)
LINK_PAT = re.compile(r"https?://")
# Credential phishing / account-takeover bait: never comply, say so plainly.
CREDENTIAL_PAT = re.compile(
    r"\b(password|passcode|log\s*in\s*for\s*me|verify\s*(your|my)\s*account|"
    r"it\s*wasn'?t\s*me|recovery\s*code|2fa|two.?factor)\b", re.I)
SCAM_PAT = re.compile(
    r"\b(crypto|bitcoin|btc|eth\b|wallet|giveaway|doubl(e|ing)\s*your|"
    r"investment\s*opportunity|guaranteed\s*returns?)\b", re.I)


def classify(text):
    """Return (intent, detail). Intent is informational only."""
    t = (text or "").strip()
    low = t.lower()
    if CREDENTIAL_PAT.search(low):
        return "credential_bait", "asks about passwords/logins/codes"
    if SCAM_PAT.search(low):
        return "scam", "money/crypto bait"
    if VOICE_PAT.search(low):
        return "voice_request", "explicit voice note ask"
    if VIDEO_PAT.search(low):
        return "video_request", "explicit video ask"
    if IMAGE_PAT.search(low):
        return "image_request", "explicit image ask"
    if GREETING_PAT.match(low) and len(t) <= 30:
        return "greeting", "short greeting"
    if THANKS_PAT.search(low) and len(t) <= 60:
        return "thanks", "short thanks"
    if t.endswith("?") or QUESTION_PAT.match(low):
        return "question", "needs an answer"
    if LINK_PAT.search(t):
        return "link_share", "shared a link"
    return "other", "no strong signal"


# Templates are casual-direct, first person, as the account owner.
# {sender} is the correspondent's handle when known.
_TEMPLATES = {
    "greeting": "hey! what's going on?",
    "thanks": "anytime. glad it helped.",
    "question": ("good question. let me look into that and get back "
                 "to you properly."),
    "link_share": "got the link. I'll take a look.",
    "other": "got it. I'll check and get back to you.",
    "voice_request": ("can't send voice notes from here, so text it is. "
                      "what's the question?"),
    "image_request": ("can't send pictures from here. describe what you "
                      "need and I'll talk it through in text."),
    "video_request": ("can't send videos from here. happy to explain "
                      "in text though, what's up?"),
    "credential_bait": ("I can't help with passwords or logins over DM. "
                        "for account stuff, use the platform's own recovery."),
    "scam": ("hmm, not touching that one. what did you actually need?"),
}

SAFE_FALLBACK = "got it. I'll get back to you."


def _gates_ok(home, platform, account_label, draft):
    """Run the repo's content gates over a draft. Returns (ok, notes)."""
    notes = []
    try:
        from security import secrets as secrets_mod
        found, what = secrets_mod.contains_secret(draft)
        if found:
            return False, [f"secret leak: {what}"]
    except Exception as e:
        notes.append(f"secrets gate error: {e}")
    try:
        from identity import check as identity_mod
        ident = identity_mod.check_identity(draft, account_label, home)
        if isinstance(ident, dict) and not ident.get("pass", True):
            return False, [f"identity gate: {ident}"]
    except Exception as e:
        notes.append(f"identity gate error: {e}")
    try:
        from voice import check as voice_check_mod
        v = voice_check_mod.check_text(draft, platform)
        if isinstance(v, dict) and not v.get("human", True):
            notes.append(f"voice flags: {v.get('flags')}")
    except Exception as e:
        notes.append(f"voice gate error: {e}")
    return True, notes


def draft_reply(home, platform, account_label, inbound_text, sender=""):
    """Draft a reply to one inbound DM.

    Returns (draft_text, info). draft_text is style-gated. info carries
    intent, risk (normal|high), media_requested, fallback_used, gate notes.
    The draft is a candidate for the approvals queue — never sent directly.
    """
    intent, detail = classify(inbound_text)
    risk = "high" if intent in ("credential_bait", "scam") else "normal"
    media_requested = intent in ("voice_request", "image_request",
                                 "video_request")
    # No TTS and no image/video generation exist in this repo, so media
    # requests always take the honest plain-language fallback path inside
    # the reply text (spec: never go silent).
    fallback_used = media_requested
    draft = _TEMPLATES.get(intent, _TEMPLATES["other"])
    ok, notes = _gates_ok(home, platform, account_label, draft)
    if not ok:
        draft = SAFE_FALLBACK
        notes = ["template refused by gates; used safe fallback"] + notes
    draft = style_mod.gate(draft)
    return draft, {
        "intent": intent,
        "detail": detail,
        "risk": risk,
        "media_requested": media_requested,
        "fallback_used": fallback_used,
        "gate_notes": notes,
        "sender": sender,
    }
