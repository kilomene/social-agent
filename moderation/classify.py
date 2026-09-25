"""Lexicon-based comment classifiers (pure stdlib).

classify_comment(text) -> {"label", "score", "reasons"}
  label: ok | question | praise | spam | toxic
  score: 0-100 severity (higher = more severe)
  reasons: human-readable matched signals

check_auto_hide(text, rules) -> matched rule dict or None
  rules: [{"pattern": "...", "label": "...", "reason": "..."}] from
  policy.yaml moderation.auto_hide. Substring match, case-insensitive.

The built-in lexicons are a minimal seed. Users extend them via policy.yaml
(moderation.auto_hide) and never by editing this file in the repo.
"""

import re

LABELS = ("ok", "question", "praise", "spam", "toxic")

# ------------------------------------------------------------------ spam --

_SPAM_PATTERNS = [
    (r"https?://", "contains URL"),
    (r"www\.", "contains URL"),
    (r"\bt\.me/", "telegram link"),
    (r"\bbit\.ly/", "shortened link"),
    (r"\bwa\.me/", "whatsapp link"),
    (r"\bdm me\b", "DM-me solicitation"),
    (r"\bmessage me\b", "DM-me solicitation"),
    (r"\bwhatsapp\b", "off-platform contact push"),
    (r"\btelegram\b", "off-platform contact push"),
    (r"\bfree crypto\b", "crypto giveaway pattern"),
    (r"\bcrypto giveaway\b", "crypto giveaway pattern"),
    (r"\bairdrop\b", "crypto giveaway pattern"),
    (r"\bdouble your\b", "money-doubling scam pattern"),
    (r"\bsend .*?(eth|btc|usdt|usdc|sol)\b", "crypto payment request"),
    (r"\bfree followers\b", "follower-selling spam"),
    (r"\bbuy followers\b", "follower-selling spam"),
    (r"\bget rich\b", "get-rich-quick spam"),
    (r"\bearn \$\d", "money-promise spam"),
    (r"\bmake money fast\b", "money-promise spam"),
    (r"\bcash ?app\b.*\$", "payment-app scam"),
]

_REPEAT_WORD = re.compile(r"\b(\w{3,})\b(?:\s+\1\b){2,}", re.IGNORECASE)
_REPEAT_CHAR = re.compile(r"(.)\1{5,}")


def _spam_score(text):
    low = text.lower()
    reasons = []
    for rx, why in _SPAM_PATTERNS:
        if re.search(rx, low):
            reasons.append(why)
    if _REPEAT_WORD.search(text):
        reasons.append("repetitive phrasing (same word 3+ times)")
    if _REPEAT_CHAR.search(text):
        reasons.append("repetitive characters (5+ in a row)")
    return reasons


# ----------------------------------------------------------------- toxic --

# Minimal seed lists. Extend via policy.yaml moderation.auto_hide, not here.
_PROFANITY = [
    "fuck", "fucking", "shit", "bitch", "asshole", "dick", "pussy",
    "bastard", "whore", "slut", "cunt", "retard", "retarded",
]

# Severe, unambiguous slurs only (seed list; extend in policy, not in code).
_SLURS = [
    "nigger", "nigga", "faggot", "kike", "chink", "spic", "gook",
    "raghead", "tranny",
]

_THREATS = [
    r"\bkill yourself\b",
    r"\bkys\b",
    r"\bi will kill\b",
    r"\bi'll kill\b",
    r"\bi hope you die\b",
    r"\bwish you were dead\b",
    r"\bdoxx",
    r"\bswat(ting)?\b",
]

_HATE_PATTERNS = [
    (r"\bgo back to\b", "xenophobic 'go back' pattern"),
    (r"\bsubhuman\b", "dehumanizing language"),
    (r"\b(all|you) (jews|muslims|blacks|whites|asians|gays) are\b",
     "group-targeted hate pattern"),
]


def _toxic_signals(text):
    low = text.lower()
    reasons = []
    for s in _SLURS:
        if re.search(r"\b" + re.escape(s) + r"\b", low):
            reasons.append(f"slur detected: {s}")
    for p in _PROFANITY:
        if re.search(r"\b" + re.escape(p) + r"\b", low):
            reasons.append(f"profanity: {p}")
    for rx in _THREATS:
        if re.search(rx, low):
            reasons.append("threat / self-harm encouragement pattern")
    for rx, why in _HATE_PATTERNS:
        if re.search(rx, low):
            reasons.append(why)
    # ALL-CAPS rage: mostly caps, long enough, with emphasis marks
    letters = [c for c in text if c.isalpha()]
    if len(letters) >= 15:
        caps = sum(1 for c in letters if c.isupper())
        if caps / len(letters) >= 0.75 and "!" in text:
            reasons.append("ALL-CAPS rage pattern")
    return reasons


# --------------------------------------------------------------- question --

_QUESTION_OPENERS = re.compile(
    r"(?i)^\s*(who|what|when|where|why|how|can|could|do|does|did|is|are|"
    r"was|were|will|would|should)\b"
)
_QUESTION_PHRASES = [
    "how do i", "how do you", "can you", "could you", "please explain",
    "tutorial", "what settings", "which app", "where can i",
]


def _is_question(text):
    t = text.strip()
    if t.endswith("?"):
        return True
    if _QUESTION_OPENERS.match(t):
        return True
    low = t.lower()
    return any(p in low for p in _QUESTION_PHRASES)


# ----------------------------------------------------------------- praise --

_PRAISE_WORDS = [
    "love", "amazing", "awesome", "fire", "goat", "inspiring", "incredible",
    "best", "legend", "talented", "beautiful", "congrats", "congratulations",
    "obsessed", "masterpiece", "genius", "perfect", "stunning",
]
_PRAISE_EMOJI = ["🔥", "❤️", "👏", "💯", "🙌", "✨", "😍"]


def _is_praise(text):
    low = text.lower()
    words = sum(1 for w in _PRAISE_WORDS if re.search(r"\b" + w + r"\b", low))
    emoji = sum(1 for e in _PRAISE_EMOJI if e in text)
    return (words + emoji) >= 1 and len(text.strip()) <= 160


# ---------------------------------------------------------------- classify --

def classify_comment(text):
    """Classify one comment. Returns {"label", "score", "reasons"}."""
    text = text or ""
    reasons = _toxic_signals(text)
    if reasons:
        return {"label": "toxic", "score": min(100, 60 + 10 * len(reasons)),
                "reasons": reasons}
    reasons = _spam_score(text)
    if reasons:
        return {"label": "spam", "score": min(95, 45 + 10 * len(reasons)),
                "reasons": reasons}
    if _is_question(text):
        return {"label": "question", "score": 10,
                "reasons": ["reads as a question (feeds content-idea watcher)"]}
    if _is_praise(text):
        return {"label": "praise", "score": 5,
                "reasons": ["reads as praise (feeds sentiment watcher)"]}
    return {"label": "ok", "score": 0, "reasons": ["no moderation signal"]}


def check_auto_hide(text, rules):
    """Match text against pre-approved auto-hide rules from policy.yaml.

    rules: list of {"pattern", "label", "reason"} dicts (or bare strings,
    which match as case-insensitive substrings labeled "custom").
    Returns the matched rule dict or None.
    """
    low = (text or "").lower()
    for r in rules or []:
        if isinstance(r, str):
            pat, rule = r, {"pattern": r, "label": "custom",
                            "reason": "matched pre-approved auto-hide pattern"}
        else:
            pat = str(r.get("pattern", ""))
            rule = {"pattern": pat, "label": r.get("label", "custom"),
                    "reason": r.get("reason", "matched pre-approved auto-hide rule")}
        if pat and pat.lower() in low:
            return rule
    return None
