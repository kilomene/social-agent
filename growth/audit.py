"""Account growth audit (pure stdlib).

`audit(platform, account, inputs)` scores the account across five pillars and
returns prioritized fixes. Works fully offline: it combines user-supplied
numbers with whatever watcher/analytics state exists. Pillars with no data
are reported as "unknown" (never guessed) with a fix telling the user which
metric to supply.
"""

PILLARS = ("consistency", "hooks", "niche_clarity", "engagement_rate",
           "profile_conversion")


def _score_consistency(posts_per_week):
    if posts_per_week is None:
        return None, "supply --posts-per-week"
    ppw = float(posts_per_week)
    if ppw >= 7:
        s = 100
    elif ppw >= 5:
        s = 90
    elif ppw >= 3:
        s = 70
    elif ppw >= 1:
        s = 45
    else:
        s = 10
    return s, f"{ppw:g} posts/week"


def _score_hooks(avg_views, followers):
    # Hook strength proxy: views relative to follower base (browse/discovery).
    if avg_views is None or followers is None:
        return None, "supply --avg-views and --followers"
    ratio = float(avg_views) / max(float(followers), 1)
    if ratio >= 2.0:
        s = 100
    elif ratio >= 1.0:
        s = 80
    elif ratio >= 0.5:
        s = 60
    elif ratio >= 0.2:
        s = 40
    else:
        s = 20
    return s, f"avg views {avg_views:g} = {ratio:.1f}x follower base"


def _score_niche(niche, mission_topics=None):
    if not niche:
        return None, "supply --niche 'what your account is about in one line'"
    words = [w for w in niche.strip().split() if len(w) > 2]
    base = 40 + min(len(words), 12) * 4  # specific > vague
    bonus = 0
    if mission_topics:
        low = niche.lower()
        hits = sum(1 for t in mission_topics if t.lower() in low)
        bonus = min(hits * 10, 20)
    return min(base + bonus, 100), f"niche statement: {niche.strip()[:60]}"


def _score_engagement(avg_likes, avg_comments, avg_views):
    if avg_likes is None or avg_views is None:
        return None, "supply --avg-likes and --avg-views"
    comments = float(avg_comments or 0)
    rate = (float(avg_likes) + comments * 3) / max(float(avg_views), 1) * 100
    if rate >= 6:
        s = 100
    elif rate >= 3:
        s = 70
    elif rate >= 1:
        s = 40
    else:
        s = 20
    return s, f"engagement rate {rate:.1f}% (likes + 3x comments per view)"


def _score_profile(has_bio, has_link, has_avatar, has_cta):
    parts = [has_bio, has_link, has_avatar, has_cta]
    if all(p is None for p in parts):
        return None, "supply --has-bio/--has-link/--has-avatar/--has-cta"
    s = sum(25 for p in parts if p)
    missing = [n for n, p in zip(("bio", "link", "avatar", "CTA"), parts) if not p]
    detail = f"{s}/100" + (f" — missing: {', '.join(missing)}" if missing else " — complete")
    return s, detail


FIX_ADVICE = {
    "consistency": "Pick a cadence you can sustain for 90 days (see growth playbook) and batch-create content.",
    "hooks": "Rewrite first 2 seconds / titles around one bold promise; test 3 hook variants per week.",
    "niche_clarity": "One account = one niche. Write the one-line promise a stranger would repeat about you.",
    "engagement_rate": "Reply to every genuine comment in the first hour; end posts with a real question.",
    "profile_conversion": "Bio = who + what + proof; add link + CTA so profile visits convert to follows.",
}


def audit(platform, account, inputs, mission_topics=None):
    """Score the account. `inputs` is a dict of metric names to values.

    Returns {"platform", "account", "pillars": {name: {"score"|None, "detail"}},
    "overall": float|None, "fixes": [..]}. Fixes are sorted by pillar score
    (worst first); unknown pillars rank last with a "supply the metric" fix.
    """
    scores = {}
    scores["consistency"] = _score_consistency(inputs.get("posts_per_week"))
    scores["hooks"] = _score_hooks(inputs.get("avg_views"), inputs.get("followers"))
    scores["niche_clarity"] = _score_niche(inputs.get("niche"), mission_topics)
    scores["engagement_rate"] = _score_engagement(
        inputs.get("avg_likes"), inputs.get("avg_comments"), inputs.get("avg_views"))
    scores["profile_conversion"] = _score_profile(
        inputs.get("has_bio"), inputs.get("has_link"),
        inputs.get("has_avatar"), inputs.get("has_cta"))

    pillars = {}
    known = []
    for name in PILLARS:
        s, detail = scores[name]
        pillars[name] = {"score": s, "detail": detail}
        if s is not None:
            known.append(s)

    overall = round(sum(known) / len(known), 1) if known else None

    def sort_key(name):
        s = pillars[name]["score"]
        return (s is None, s if s is not None else 0)

    fixes = []
    for name in sorted(PILLARS, key=sort_key):
        s = pillars[name]["score"]
        if s is None:
            fixes.append(f"[{name}] unknown — {pillars[name]['detail']}.")
        else:
            fixes.append(f"[{name}] {s}/100 — {FIX_ADVICE[name]}")

    return {
        "platform": platform,
        "account": account,
        "pillars": pillars,
        "overall": overall,
        "fixes": fixes,
    }
