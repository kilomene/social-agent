"""AI-ness checker for draft text (pure stdlib).

`check_text(text, platform="general")` -> dict with:
  score       0-100, higher = more human
  flags       list of {"type", "match", "why"}
  suggestions list of human rewrite tips

Scoring: start at 100, subtract per flag (banned phrase -12, pattern -8,
capped so one text can't go below 0). Threshold 60: below it the CLI warns.
"""

import json
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WARN_THRESHOLD = 60


def _load_banned():
    p = os.path.join(REPO_ROOT, "voice", "banned.json")
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _emoji_count(text):
    return len(re.findall(
        "[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF]", text))


def check_text(text, platform="general"):
    banned = _load_banned()
    flags = []
    low = text.lower()

    for phrase in banned["banned_phrases"]:
        if phrase in low:
            flags.append({"type": "banned_phrase", "match": phrase,
                          "why": "reads as AI-generated filler"})

    if _emoji_count(text) > 3:
        flags.append({"type": "emoji_spam",
                      "match": f"{_emoji_count(text)} emojis",
                      "why": banned["banned_patterns"]["emoji_spam"]})
    if re.search(r"!{3,}", text):
        flags.append({"type": "exclamation_spam", "match": "!!!",
                      "why": banned["banned_patterns"]["exclamation_spam"]})
    if re.match(r"(?i)^\s*(in today'?s|in conclusion|overall,|moreover,|furthermore,)",
                text):
        flags.append({"type": "formal_opener", "match": text.split()[0],
                      "why": banned["banned_patterns"]["formal_opener"]})
    tags = re.findall(r"#\w+", text)
    if len(tags) > 5 and platform in ("x", "tiktok", "general"):
        flags.append({"type": "hashtag_stuffing", "match": f"{len(tags)} hashtags",
                      "why": banned["banned_patterns"]["hashtag_stuffing"]})
    hedges = len(re.findall(r"(?i)\b(however|although|on the other hand|"
                            r"that said|nevertheless)\b", text))
    if hedges >= 3:
        flags.append({"type": "hedged_to_death", "match": f"{hedges} hedges",
                      "why": banned["banned_patterns"]["hedged_to_death"]})
    # All-caps shouting (excluding short acronyms)
    caps_words = [w for w in re.findall(r"\b[A-Z]{4,}\b", text)]
    if caps_words:
        flags.append({"type": "shouting", "match": caps_words[0],
                      "why": "all-caps words read as spammy/bot-like"})
    # Robotic sign-offs
    if re.search(r"(?i)(hope this helps|let me know if (you|u) need)", text):
        flags.append({"type": "robotic_signoff",
                      "match": "support-bot sign-off",
                      "why": "assistant-style sign-offs don't belong in social posts"})

    score = 100
    for f in flags:
        score -= 12 if f["type"] == "banned_phrase" else 8
    score = max(0, score)

    suggestions = []
    if any(f["type"] == "banned_phrase" for f in flags):
        suggestions.append("Swap banned filler for a specific, concrete detail "
                           "only a human would know.")
    if any(f["type"] in ("emoji_spam", "exclamation_spam", "shouting")
           for f in flags):
        suggestions.append("One emoji / exclamation max — enthusiasm reads "
                           "stronger restrained.")
    if any(f["type"] == "formal_opener" for f in flags):
        suggestions.append("Open mid-thought, like a text to a friend — never "
                           "with an essay opener.")
    if any(f["type"] == "hedged_to_death" for f in flags):
        suggestions.append("Take one clear stance. Humans have opinions; "
                           "hedging everything reads synthetic.")
    if not suggestions and score < 100:
        suggestions.append("Add one specific detail (a number, a name, a "
                           "moment) — specificity is the fastest human signal.")
    if score == 100:
        suggestions.append("Reads human. Ship it.")

    return {
        "score": score,
        "human": score >= WARN_THRESHOLD,
        "flags": flags,
        "suggestions": suggestions,
        "platform": platform,
    }
