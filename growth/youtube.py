"""YouTube deep support: quality gate, title optimizer, description builder,
thumbnail briefs (pure stdlib).

Nothing here generates images or publishes anything. `preflight` is a
pre-publish QUALITY GATE: it refuses to approve a video post whose metadata
is missing required quality fields. Title/description/thumbnail helpers are
packaging tools the creator reviews and approves like any other draft.
"""

# Pre-publish quality checklist. `required=True` fields block approval.
QUALITY_CHECKLIST = [
    {"key": "title", "label": "Title written and hook-checked", "required": True},
    {"key": "thumbnail", "label": "Custom thumbnail designed (not auto-frame)", "required": True},
    {"key": "hook_30s", "label": "First 30 seconds pay off the title's promise", "required": True},
    {"key": "resolution", "label": "Exported >= 1080p", "required": True},
    {"key": "audio", "label": "Clean audio: levels normalized, no clipping/hum", "required": True},
    {"key": "retention_edit", "label": "Retention edit: no dead air, visual change every 3-8s", "required": False},
    {"key": "description", "label": "Description with keywords, timestamps, links", "required": False},
    {"key": "end_screen", "label": "End screen points to next logical video", "required": False},
    {"key": "captions", "label": "Captions/subtitles added or reviewed", "required": False},
]

TITLE_MAX_LEN = 60  # keep under ~60 chars so titles don't truncate in search

_HOOK_FORMULAS = [
    ("number", lambda idea: f"{idea}: 7 Things Nobody Tells You"),
    ("howto", lambda idea: f"How to {idea} (Step-by-Step)"),
    ("mistake", lambda idea: f"Stop Doing {idea} Wrong — Do This Instead"),
    ("result", lambda idea: f"I Tried {idea} for 30 Days — Here's What Happened"),
    ("question", lambda idea: f"{idea}: Worth It in 2026?"),
]


def _title_score(title, keyword=""):
    s = 50
    n = len(title)
    if 35 <= n <= TITLE_MAX_LEN:
        s += 15
    elif n < 35:
        s += 5
    else:
        s -= 10  # truncates
    low = title.lower()
    if keyword and keyword.lower() in low:
        # keyword in first half = better placement
        s += 15 if low.index(keyword.lower()) < n / 2 else 8
    if any(w in low for w in ("how", "why", "what", "stop", "?")):
        s += 8  # curiosity gap
    if any(ch.isdigit() for ch in title):
        s += 7  # numbers lift CTR
    if title == title.upper() and len(title) > 10:
        s -= 15  # all-caps reads spammy
    return max(0, min(100, s))


def title_variants(raw_idea, keyword=""):
    """Generate 5 scored title variants from a raw idea string.

    Returns [{"title", "formula", "score"}] sorted by score desc.
    """
    idea = raw_idea.strip().rstrip(".")
    kw = keyword.strip() or idea.split()[0]
    out = []
    for name, fn in _HOOK_FORMULAS:
        t = fn(idea)
        out.append({"title": t, "formula": name,
                    "score": _title_score(t, kw)})
    out.sort(key=lambda v: -v["score"])
    return out


def build_description(title, summary="", timestamps=None, links=None,
                      cta="", hashtags=None):
    """Build an SEO-structured YouTube description."""
    timestamps = timestamps or []
    links = links or []
    hashtags = hashtags or []
    lines = [title, ""]
    if summary:
        lines += [summary, ""]
    if timestamps:
        lines.append("TIMESTAMPS")
        for ts in timestamps:
            lines.append(f"{ts}")
        lines.append("")
    if links:
        lines.append("LINKS")
        for label, url in links:
            lines.append(f"{label}: {url}")
        lines.append("")
    if cta:
        lines += [cta, ""]
    lines.append("Subscribe for more — new videos every week.")
    if hashtags:
        lines.append(" ".join("#" + h.lstrip("#") for h in hashtags[:5]))
    return "\n".join(lines).rstrip("\n")


def thumbnail_brief(topic, style="bold minimal", text_overlay=""):
    """Return a precise thumbnail design brief (for a designer or image tool).

    This function writes words, not pixels: a spec sheet the creator (or an
    image generator they run themselves) executes.
    """
    words = text_overlay.strip() or " ".join(topic.split()[:3]).upper()
    return "\n".join([
        f"THUMBNAIL BRIEF — {topic}",
        "",
        "Canvas: 1280x720 (16:9). Keep key elements inside the center 1200x660",
        "safe zone (edges get cropped on mobile/TV).",
        f"Style: {style}.",
        "Composition:",
        "  - One clear focal subject, large in frame (face/emotion preferred).",
        "  - High contrast: subject pops against background; avoid busy backgrounds.",
        f"  - Text overlay: \"{words}\" — max 3-4 words, huge bold sans-serif,",
        "    2-3 colors max, readable at 120px wide.",
        "  - Emotion/curiosity: expressive face or striking before/after contrast.",
        "Do NOT:",
        "  - Use tiny text, more than 4 words, or low-contrast color pairs.",
        "  - Use clickbait that the video doesn't deliver (kills retention).",
        "Check at thumbnail size: if you can't read it squinting, redo it.",
    ])


def preflight(meta):
    """Quality gate. `meta` maps checklist keys to truthy/falsy values.

    Returns (ok: bool, missing: [labels]). Required items missing -> not ok.
    """
    missing = [item["label"] for item in QUALITY_CHECKLIST
               if item["required"] and not meta.get(item["key"])]
    return (not missing), missing
