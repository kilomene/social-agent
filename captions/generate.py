"""Caption generator: hooks + body + CTA + hashtags per platform norms.

generate(platform, topic, tone, seed=0, extra_hashtags=()) -> caption dict
variants(platform, topic, tone, n=5, extra_hashtags=()) -> list of captions

Tones map to voice profiles: bold | playful | educational | calm.
Every output passes through content_gates() in the CLI (voice + identity +
secrets) before drafting — the generator itself only shapes structure.
"""

import re

PLATFORM_NORMS = {
    "tiktok":    {"hashtags": (3, 5), "max_chars": 2200, "emoji_max": 2,
                 "cta": "Follow for part {n} — I post these daily.",
                 "tag_style": "niche + broad mix"},
    "instagram": {"hashtags": (5, 10), "max_chars": 2200, "emoji_max": 2,
                 "cta": "Save this for later — you'll want it.",
                 "tag_style": "niche cluster"},
    "x":         {"hashtags": (1, 2), "max_chars": 280, "emoji_max": 1,
                 "cta": "Repost if this helped.",
                 "tag_style": "one broad tag max"},
    "youtube":   {"hashtags": (2, 3), "max_chars": 5000, "emoji_max": 1,
                 "cta": "Subscribe — new breakdowns every week.",
                 "tag_style": "topic tags only"},
    "facebook":  {"hashtags": (1, 2), "max_chars": 2000, "emoji_max": 2,
                 "cta": "Share this with someone who needs it.",
                 "tag_style": "minimal"},
    "reddit":    {"hashtags": (0, 0), "max_chars": 40000, "emoji_max": 0,
                 "cta": "Happy to answer questions below.",
                 "tag_style": "no hashtags on reddit"},
}

TONES = ("bold", "playful", "educational", "calm")

# Hook formulas: {topic} is interpolated. Written first-person as the owner.
_HOOKS = [
    "I spent 6 hours testing {topic} so you don't have to.",
    "Nobody talks about {topic} like this.",
    "This {topic} trick took me from stuck to shipping.",
    "{topic}, but explained like you're five.",
    "Stop doing {topic} the hard way.",
    "The {topic} workflow I wish someone gave me a year ago.",
    "POV: {topic} finally clicks.",
    "I was wrong about {topic}. Here's what actually works.",
    "{topic} in 30 seconds — save this.",
    "Ranking every {topic} method I've tried (worst to best).",
]

_BODY_TEMPLATES = {
    "bold": ("Here's the exact setup I run:\n1. {step1}\n2. {step2}\n3. {step3}\n"
             "No fluff. Try it and tell me I'm wrong."),
    "playful": ("Okay so I may have gone a little overboard with {topic} 😅\n"
                "but the results?? worth it. Full breakdown below."),
    "educational": ("Quick breakdown of {topic}:\n• What it is\n• Why it works\n"
                    "• The one mistake everyone makes\nLet's get into it."),
    "calm": ("A short note on {topic}.\nTook my time with this one — "
             "quality over quantity, always."),
}

_CTA_VARIANTS = [
    "{cta}",
    "{cta} Comment \"MORE\" and I'll do a part 2.",
    "{cta} What's your take — agree or disagree?",
]


def _slugify_topic(topic):
    words = re.findall(r"[a-z0-9]+", topic.lower())
    return "".join(w.capitalize() for w in words[:3]) or "Topic"


def suggest_hashtags(platform, topic, extra=()):
    """Deterministic hashtag set from the topic + extras, honoring norms."""
    norms = PLATFORM_NORMS[platform]
    lo, hi = norms["hashtags"]
    words = re.findall(r"[a-z0-9]+", topic.lower())
    tags = []
    # topic-derived tags first (camel-ish join of 1-2 words)
    for i, w in enumerate(words):
        if len(tags) >= hi:
            break
        tag = w if i == 0 else words[0] + w.capitalize()
        if tag not in tags:
            tags.append(tag)
    for h in extra:
        h = h.strip().lstrip("#").lower().replace(" ", "")
        if h and h not in tags and len(tags) < hi:
            tags.append(h)
    return ["#" + t for t in tags[:hi]]


def generate(platform, topic, tone="bold", seed=0, extra_hashtags=()):
    """Build one caption dict. Deterministic per (platform, topic, tone, seed)."""
    if platform not in PLATFORM_NORMS:
        raise ValueError(f"unknown platform {platform!r}")
    if tone not in TONES:
        raise ValueError(f"unknown tone {tone!r} (pick: {', '.join(TONES)})")
    norms = PLATFORM_NORMS[platform]
    hook = _HOOKS[seed % len(_HOOKS)].format(topic=topic)
    body = _BODY_TEMPLATES[tone].format(
        topic=topic, step1="nail the hook in the first 3 seconds",
        step2="keep one idea per cut", step3="end on the payoff, not the setup")
    cta = _CTA_VARIANTS[seed % len(_CTA_VARIANTS)].format(
        cta=norms["cta"].format(n=2))
    tags = suggest_hashtags(platform, topic, extra_hashtags)
    caption = f"{hook}\n\n{body}\n\n{cta}"
    if tags:
        caption += "\n\n" + " ".join(tags)
    if len(caption) > norms["max_chars"]:
        caption = caption[:norms["max_chars"] - 1] + "…"
    return {
        "platform": platform, "topic": topic, "tone": tone, "seed": seed,
        "hook": hook, "body": body, "cta": cta,
        "hashtags": tags, "caption": caption,
        "char_count": len(caption),
        "norms": {"hashtags": norms["hashtags"], "max_chars": norms["max_chars"],
                  "tag_style": norms["tag_style"]},
    }


def variants(platform, topic, tone="bold", n=5, extra_hashtags=()):
    """n caption variants (different hooks/CTAs) for A/B testing."""
    return [generate(platform, topic, tone, seed=i,
                     extra_hashtags=extra_hashtags) for i in range(max(1, n))]
