"""Platform adapter interface.

An adapter describes one social platform: what can be *read* (via browser
automation), what can be *posted*, how auth works, and the rate limits
social-agent enforces. There is no API backend anywhere in this repo —
adapters are descriptive + fixture-based: they never hold credentials and
never perform live network calls themselves. Live reading/posting happens
in a real browser session driven by the user's agent; the adapter tells
that agent exactly what is possible.
"""

SUPPORTED_PLATFORMS = ["tiktok", "x", "instagram", "facebook", "youtube", "reddit", "linkedin"]


class AdapterSpec:
    """Declarative spec for one platform."""

    def __init__(self, name, display, auth, readable, postable, not_possible,
                 rate_note, docs):
        self.name = name
        self.display = display
        self.auth = auth                    # how sign-in works (descriptive)
        self.readable = readable            # list of readable surfaces
        self.postable = postable            # list of postable actions
        self.not_possible = not_possible    # honest gaps
        self.rate_note = rate_note
        self.docs = docs                    # official docs URLs

    def to_dict(self):
        return {
            "name": self.name,
            "display": self.display,
            "auth": self.auth,
            "readable": self.readable,
            "postable": self.postable,
            "not_possible": self.not_possible,
            "rate_note": self.rate_note,
            "docs": self.docs,
        }


def get_adapter(name):
    from . import tiktok, x, instagram, facebook, youtube, reddit, linkedin
    mods = {
        "tiktok": tiktok, "x": x, "instagram": instagram,
        "facebook": facebook, "youtube": youtube, "reddit": reddit,
        "linkedin": linkedin,
    }
    key = name.lower()
    if key not in mods:
        raise KeyError(f"unknown platform: {name} (supported: {', '.join(SUPPORTED_PLATFORMS)})")
    return mods[key].ADAPTER
