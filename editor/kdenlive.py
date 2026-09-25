"""Kdenlive project model. Kdenlive .kdenlive files are MLT XML.

This builds valid MLT XML that Kdenlive opens directly: a bin of producers,
a multitrack timeline (tractor), clips with in/out points, and named effects
(MLT filters with Kdenlive effect ids). Complex keyframed animation is finished
in the Kdenlive GUI — see editor/KDENLIVE.md.

No kdenlive/melt binary is required to *author* projects. Headless rendering
via `melt` is used only if the binary exists (checked at runtime).
"""

import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

PROFILES = {
    # name: MLT profile attributes
    "1080p30": {"width": "1920", "height": "1080", "progressive": "1",
                "sample_aspect_num": "1", "sample_aspect_den": "1",
                "display_aspect_num": "16", "display_aspect_den": "9",
                "frame_rate_num": "30", "frame_rate_den": "1",
                "colorspace": "709"},
    "1080p60": {"width": "1920", "height": "1080", "progressive": "1",
                "sample_aspect_num": "1", "sample_aspect_den": "1",
                "display_aspect_num": "16", "display_aspect_den": "9",
                "frame_rate_num": "60", "frame_rate_den": "1",
                "colorspace": "709"},
    "4k30": {"width": "3840", "height": "2160", "progressive": "1",
             "sample_aspect_num": "1", "sample_aspect_den": "1",
             "display_aspect_num": "16", "display_aspect_den": "9",
             "frame_rate_num": "30", "frame_rate_den": "1",
             "colorspace": "709"},
    "vertical1080": {"width": "1080", "height": "1920", "progressive": "1",
                     "sample_aspect_num": "1", "sample_aspect_den": "1",
                     "display_aspect_num": "9", "display_aspect_den": "16",
                     "frame_rate_num": "30", "frame_rate_den": "1",
                     "colorspace": "709"},
}

# Kdenlive effect id -> MLT service + default params. These are real Kdenlive
# effect names (Effects panel) and their underlying MLT services.
EFFECTS = {
    "color-balance": {"service": "movit.colour_balance",
                      "kdenlive_id": "colour_balance",
                      "desc": "Color Balance (Lift/Gamma/Gain style lift-gamma-gain)"},
    "lift-gamma-gain": {"service": "lift_gamma_gain",
                        "kdenlive_id": "lift_gamma_gain",
                        "desc": "Lift Gamma Gain — the classic cinematic primary grade"},
    "color-grading": {"service": "frei0r.coloradj_RGB",
                      "kdenlive_id": "frei0r.coloradj_RGB",
                      "desc": "Color Adjustment (frei0r) — brightness/contrast per channel"},
    "vignette": {"service": "frei0r.vignette",
                 "kdenlive_id": "frei0r.vignette",
                 "desc": "Vignette"},
    "blur": {"service": "frei0r.blur",
             "kdenlive_id": "frei0r.blur",
             "desc": "Blur (keyframeable)"},
    "glow": {"service": "frei0r.glow",
             "kdenlive_id": "frei0r.glow",
             "desc": "Glow — neon bloom for night footage"},
    "chroma-key": {"service": "frei0r.select0r",
                   "kdenlive_id": "frei0r.select0r",
                   "desc": "Chroma key (select0r)"},
    "transform": {"service": "affine",
                  "kdenlive_id": "affine",
                  "desc": "Transform: position/scale/rotation with keyframes"},
    "fade-in": {"service": "brightness",
                "kdenlive_id": "brightness",
                "desc": "Fade from black (animated brightness)"},
    "fade-out": {"service": "brightness",
                 "kdenlive_id": "brightness",
                 "desc": "Fade to black (animated brightness)"},
}


def _prop(parent, name, value):
    p = ET.SubElement(parent, "property", {"name": name})
    p.text = str(value)
    return p


class Project:
    """In-memory Kdenlive/MLT project; save() writes .kdenlive XML."""

    def __init__(self, title="untitled", profile="1080p30"):
        if profile not in PROFILES:
            raise ValueError(f"unknown profile {profile!r} "
                             f"(pick: {', '.join(sorted(PROFILES))})")
        self.title = title
        self.profile = profile
        self.assets = []      # [{"id", "path", "kind"}]
        self.timeline = []    # [{"clip_id", "asset_id", "track", "in", "out", "effects": []}]
        self._next_asset = 1
        self._next_clip = 1
        self.markers = []     # [{"time", "comment"}]
        self.notes = ""

    # ------------------------------------------------------------ assets ---
    def add_asset(self, path, kind=None):
        """Register a media file in the project bin."""
        if not path:
            raise ValueError("asset path is required")
        ext = os.path.splitext(path)[1].lower()
        kind = kind or ("audio" if ext in (".mp3", ".wav", ".flac", ".aac", ".ogg")
                        else "image" if ext in (".png", ".jpg", ".jpeg", ".svg", ".gif")
                        else "video")
        aid = f"asset{self._next_asset}"
        self._next_asset += 1
        self.assets.append({"id": aid, "path": path, "kind": kind})
        return aid

    def asset(self, aid):
        for a in self.assets:
            if a["id"] == aid:
                return a
        raise ValueError(f"unknown asset {aid!r}")

    # ---------------------------------------------------------- timeline ---
    def add_clip(self, asset_id, track="v1", in_s=0.0, out_s=None):
        """Place an asset on a timeline track (v1/v2/a1/a2)."""
        a = self.asset(asset_id)
        if track.startswith("v") and a["kind"] == "audio":
            raise ValueError(f"audio asset {asset_id} cannot go on video track {track}")
        if track.startswith("a") and a["kind"] in ("video", "image"):
            raise ValueError(f"visual asset {asset_id} cannot go on audio track {track}")
        cid = f"clip{self._next_clip}"
        self._next_clip += 1
        self.timeline.append({"clip_id": cid, "asset_id": asset_id,
                              "track": track, "in": float(in_s),
                              "out": float(out_s) if out_s is not None else None,
                              "effects": []})
        return cid

    def add_effect(self, clip_id, effect, params=None):
        """Attach a named effect (see EFFECTS) to a timeline clip."""
        if effect not in EFFECTS:
            raise ValueError(f"unknown effect {effect!r} "
                             f"(pick: {', '.join(sorted(EFFECTS))})")
        for c in self.timeline:
            if c["clip_id"] == clip_id:
                c["effects"].append({"effect": effect,
                                     "params": params or {},
                                     "service": EFFECTS[effect]["service"],
                                     "kdenlive_id": EFFECTS[effect]["kdenlive_id"]})
                return
        raise ValueError(f"unknown clip {clip_id!r}")

    def add_marker(self, time_s, comment=""):
        self.markers.append({"time": float(time_s), "comment": comment})

    # -------------------------------------------------------------- save ---
    def _build_xml(self):
        prof = PROFILES[self.profile]
        mlt = ET.Element("mlt", {"LC_NUMERIC": "C", "version": "7.20.0",
                                 "title": self.title,
                                 "producer": "main_bin"})
        ET.SubElement(mlt, "profile", prof)

        # --- project bin: one playlist holding all producers
        main_bin = ET.SubElement(mlt, "playlist", {"id": "main_bin"})
        _prop(main_bin, "xml_retain", "1")
        for a in self.assets:
            prod = ET.SubElement(mlt, "producer",
                                 {"id": a["id"], "in": "0", "out": "99999"})
            _prop(prod, "resource", a["path"])
            _prop(prod, "mlt_service",
                  "avformat" if a["kind"] != "image" else "qimage")
            entry = ET.SubElement(main_bin, "entry",
                                  {"producer": a["id"], "in": "0", "out": "99999"})

        # --- timeline: one playlist per track, combined by a tractor
        tracks = sorted({c["track"] for c in self.timeline})
        tractor = ET.SubElement(mlt, "tractor",
                                {"id": "timeline", "title": "Timeline",
                                 "in": "0", "out": "99999"})
        multitrack = ET.SubElement(tractor, "multitrack")
        for i, t in enumerate(tracks):
            pl = ET.SubElement(mlt, "playlist", {"id": f"playlist_{t}"})
            for c in [c for c in self.timeline if c["track"] == t]:
                a = self.asset(c["asset_id"])
                entry = ET.SubElement(pl, "entry",
                                      {"producer": a["id"],
                                       "in": str(int(c["in"] * 30)),
                                       "out": str(int((c["out"] or c["in"] + 10) * 30))})
                for fx in c["effects"]:
                    filt = ET.SubElement(entry, "filter")
                    _prop(filt, "mlt_service", fx["service"])
                    _prop(filt, "kdenlive_id", fx["kdenlive_id"])
                    for k, v in fx["params"].items():
                        _prop(filt, f"param_{k}", v)
            track_el = ET.SubElement(multitrack, "track",
                                     {"producer": f"playlist_{t}",
                                      "hide": "audio" if t.startswith("v") else "video"})
        # markers as comments on the tractor
        for m in self.markers:
            mk = ET.SubElement(tractor, "property",
                               {"name": f"kdenlive:marker:{m['time']}"})
            mk.text = m["comment"]

        _prop(mlt, "kdenlive:docproperties.version", "1")
        if self.notes:
            _prop(mlt, "kdenlive:docproperties.notes", self.notes)
        return mlt

    def save(self, path):
        """Write the .kdenlive file + an autosave sidecar."""
        tree = ET.ElementTree(self._build_xml())
        ET.indent(tree, space="  ")
        with open(path, "wb") as fh:
            tree.write(fh, encoding="utf-8", xml_declaration=True)
        sidecar = path + ".autosave"
        with open(sidecar, "w", encoding="utf-8") as fh:
            fh.write(f"autosaved {datetime.now(timezone.utc).isoformat()} "
                     f"assets={len(self.assets)} clips={len(self.timeline)}\n")
        return path

    def missing_media(self):
        """List asset paths that do not exist on disk."""
        return [a["path"] for a in self.assets if not os.path.exists(a["path"])]

    @staticmethod
    def melt_available():
        return shutil.which("melt") is not None

    @staticmethod
    def kdenlive_available():
        return shutil.which("kdenlive") is not None

    def render_headless(self, output, profile=None):
        """Render via melt if installed; else raise with GUI instructions."""
        if not self.melt_available():
            raise RuntimeError(
                "melt is not installed — open the .kdenlive file in Kdenlive "
                "and render from Project > Render (see editor/KDENLIVE.md). "
                "Install: `sudo apt install melt` (Ubuntu) for headless renders.")
        if profile is None:
            profile = self.profile
        argv = ["melt", output, "-profile", profile]
        print("RUN:", " ".join(argv))
        proc = subprocess.run(argv, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"melt failed: {proc.stderr.strip()[-400:]}")
        return output
