"""platforms/browser: per-platform browser recipes (no APIs).

Each recipe documents:
  LOGIN_NOTES  — how first login behaves on this platform
  SELECTORS    — CSS selectors for like / comment / follow / composer /
                 upload / DM thread / notifications
  QUIRKS       — known behaviors (login walls, checkpoints, rate walls)
  actions      — named action recipes: ordered primitive steps

SELECTORS ARE A MAINTENANCE SURFACE: platforms change their DOM without
notice. Re-check discipline: every recipe carries LAST_VERIFIED; when an
action starts failing, re-verify selectors against the live site before
assuming anything else is broken. Prefer role/text-based selectors over
deep class chains — they rot slower.
"""

from platforms.browser import facebook, instagram, linkedin, reddit, tiktok, x, youtube

RECIPES = {
    "facebook": facebook,
    "instagram": instagram,
    "x": x,
    "youtube": youtube,
    "reddit": reddit,
    "tiktok": tiktok,
    "linkedin": linkedin,
}


def get(platform):
    if platform not in RECIPES:
        raise KeyError(f"no browser recipe for {platform!r}")
    return RECIPES[platform]
