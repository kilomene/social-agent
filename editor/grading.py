"""Cinematic color grades as ffmpeg filtergraphs.

Presets are tuned to the reference stills in video/looks/ (see LOOKS.md):
teal shadows / orange practicals / crushed blacks / cool midtones.
`clean` is a first-class "no effect" option.
"""

GRADES = {
    "teal-noir": {
        "desc": "Signature look: teal shadows, orange practicals, crushed blacks, cool midtones (matches video/looks/ reference stills).",
        "filter": ("colorbalance=rs=-0.25:gs=0.10:bs=0.25:"
                   "rm=-0.15:gm=0.08:bm=0.15:"
                   "rh=0.05:gh=0.0:bh=-0.05,"
                   "eq=contrast=1.08:brightness=-0.02:saturation=1.15,"
                   "vignette=PI/5"),
    },
    "neon-city": {
        "desc": "Rainy neon street: deeper blue shadows, higher saturation, neon highlights protected.",
        "filter": ("colorbalance=rs=-0.30:gs=0.05:bs=0.30:"
                   "rm=-0.18:gm=0.05:bm=0.18:"
                   "rh=0.03:gh=0.02:bh=0.0,"
                   "eq=contrast=1.10:brightness=0.01:saturation=1.25,"
                   "vignette=PI/5"),
    },
    "teal-street": {
        "desc": "Teal-and-orange dusk: teal shadows/mids, warm blooming highlights.",
        "filter": ("colorbalance=rs=-0.22:gs=0.08:bs=0.22:"
                   "rm=-0.14:gm=0.06:bm=0.12:"
                   "rh=0.10:gh=0.03:bh=-0.08,"
                   "eq=contrast=1.06:brightness=0.0:saturation=1.12,"
                   "vignette=PI/6"),
    },
    "warm-vintage": {
        "desc": "Warm nostalgic film: lifted blacks, warm mids, faded contrast.",
        "filter": ("colorbalance=rs=0.08:gs=0.02:bs=-0.10:"
                   "rm=0.10:gm=0.03:bh=-0.06,"
                   "curves=m='0/0.06 0.5/0.52 1/0.96',"
                   "eq=saturation=0.85,vignette=PI/4"),
    },
    "noir": {
        "desc": "Black & white noir: crushed blacks, bright whites, hard contrast.",
        "filter": "hue=s=0,eq=contrast=1.25:brightness=-0.03,vignette=PI/4",
    },
    "blockbuster": {
        "desc": "Modern blockbuster: punchy contrast, saturated primaries, cool shadows.",
        "filter": ("colorbalance=rs=-0.12:bs=0.12:rm=-0.08:bm=0.08,"
                   "eq=contrast=1.15:saturation=1.20,"
                   "unsharp=5:5:0.6:5:5:0.0"),
    },
    "clean": {
        "desc": "No effect: passthrough, normalized to yuv420p only.",
        "filter": "format=yuv420p",
    },
}


def list_grades():
    """Return {name: desc} for every preset."""
    return {name: g["desc"] for name, g in GRADES.items()}


def filtergraph(look):
    """Return the ffmpeg -vf filtergraph for a grade name."""
    if look not in GRADES:
        raise ValueError(f"unknown grade {look!r} "
                         f"(pick: {', '.join(sorted(GRADES))})")
    return GRADES[look]["filter"]


def describe(look):
    if look not in GRADES:
        raise ValueError(f"unknown grade {look!r}")
    return GRADES[look]["desc"]
