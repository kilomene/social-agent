"""Shotcut project model. Shotcut .mlt files are also MLT XML, but simpler
than Kdenlive's: a flat structure with producers, playlists and tractors,
no Kdenlive-specific metadata.

Shotcut is the lighter-weight editor of the two: faster to open, fewer
built-in cinematic tools, excellent for quick assembly cuts. Kdenlive remains
the primary editor for full productions (see editor/KDENLIVE.md vs
editor/SHOTCUT.md).
"""

import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


def _prop(parent, name, value):
    p = ET.SubElement(parent, "property", {"name": name})
    p.text = str(value)
    return p


class Project:
    """In-memory Shotcut/MLT project; save() writes .mlt XML."""

    def __init__(self, title="untitled", width=1920, height=1080, fps=30):
        self.title = title
        self.width = width
        self.height = height
        self.fps = fps
        self.assets = []
        self.timeline = []
        self._next = 1

    def add_asset(self, path):
        if not path:
            raise ValueError("asset path is required")
        aid = f"producer{self._next}"
        self._next += 1
        self.assets.append({"id": aid, "path": path})
        return aid

    def add_clip(self, asset_id, track="v1", in_s=0.0, out_s=None):
        if not any(a["id"] == asset_id for a in self.assets):
            raise ValueError(f"unknown asset {asset_id!r}")
        cid = f"clip{self._next}"
        self._next += 1
        self.timeline.append({"clip_id": cid, "asset_id": asset_id,
                              "track": track, "in": float(in_s),
                              "out": float(out_s) if out_s is not None else None})
        return cid

    def _build_xml(self):
        mlt = ET.Element("mlt", {"LC_NUMERIC": "C", "version": "7.20.0",
                                 "title": self.title, "root": os.getcwd(),
                                 "profile": "hdv_1080_30p"})
        ET.SubElement(mlt, "profile",
                      {"description": f"{self.width}x{self.height} {self.fps}fps",
                       "width": str(self.width), "height": str(self.height),
                       "progressive": "1", "sample_aspect_num": "1",
                       "sample_aspect_den": "1",
                       "display_aspect_num": str(self.width),
                       "display_aspect_den": str(self.height),
                       "frame_rate_num": str(self.fps), "frame_rate_den": "1",
                       "colorspace": "709"})
        for a in self.assets:
            prod = ET.SubElement(mlt, "producer",
                                 {"id": a["id"], "in": "0", "out": "99999"})
            _prop(prod, "resource", a["path"])
            _prop(prod, "mlt_service", "avformat")
        tracks = sorted({c["track"] for c in self.timeline})
        tractor = ET.SubElement(mlt, "tractor",
                                {"id": "tractor", "title": "Shotcut version",
                                 "in": "0", "out": "99999"})
        _prop(tractor, "shotcut", "1")
        multitrack = ET.SubElement(tractor, "multitrack")
        for t in tracks:
            pl = ET.SubElement(mlt, "playlist", {"id": f"playlist_{t}"})
            _prop(pl, "shotcut:name", t)
            for c in [c for c in self.timeline if c["track"] == t]:
                ET.SubElement(pl, "entry",
                              {"producer": c["asset_id"],
                               "in": str(int(c["in"] * self.fps)),
                               "out": str(int((c["out"] or c["in"] + 10) * self.fps))})
            ET.SubElement(multitrack, "track", {"producer": f"playlist_{t}"})
        return mlt

    def save(self, path):
        tree = ET.ElementTree(self._build_xml())
        ET.indent(tree, space="  ")
        with open(path, "wb") as fh:
            tree.write(fh, encoding="utf-8", xml_declaration=True)
        with open(path + ".autosave", "w", encoding="utf-8") as fh:
            fh.write(f"autosaved {datetime.now(timezone.utc).isoformat()} "
                     f"assets={len(self.assets)} clips={len(self.timeline)}\n")
        return path

    def missing_media(self):
        return [a["path"] for a in self.assets if not os.path.exists(a["path"])]

    @staticmethod
    def shotcut_available():
        return shutil.which("shotcut") is not None

    def render_headless(self, output):
        """Shotcut has no headless CLI of its own; melt renders .mlt files."""
        melt = shutil.which("melt")
        if not melt:
            raise RuntimeError(
                "neither shotcut nor melt is installed — open the .mlt file in "
                "Shotcut and use Export (see editor/SHOTCUT.md).")
        argv = [melt, output, "-profile",
                f"hdv_1080_{self.fps}p"]
        print("RUN:", " ".join(argv))
        proc = subprocess.run(argv, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"melt failed: {proc.stderr.strip()[-400:]}")
        return output
