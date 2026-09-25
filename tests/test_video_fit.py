"""Tests for the smart aspect-ratio fitter (video/fit.py)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from video import fit as vfit
from video import ffmpeg as vff


def info4x3():
    return {"width": 640, "height": 480, "duration": 5.0,
            "file_size": 1000, "container": "mp4", "vcodec": "h264",
            "path": "/tmp/x.mp4"}


def test_specs_load():
    s = vfit.load_specs()
    for p in ("tiktok", "youtube", "instagram", "facebook", "x", "reddit"):
        assert p in s


def test_lookup_defaults_and_explicit():
    assert vfit.lookup("tiktok:feed")[2]["aspect"] == "9:16"
    assert vfit.lookup("youtube:long-form")[2]["aspect"] == "16:9"
    assert vfit.lookup("youtube:shorts")[2]["aspect"] == "9:16"
    assert vfit.lookup("tiktok")[1] == "feed"  # bare platform -> default placement


def test_lookup_unknown_rejected():
    with pytest.raises(ValueError):
        vfit.lookup("myspace:feed")
    with pytest.raises(ValueError):
        vfit.lookup("tiktok:stories")


def test_aspect_matches_primary_and_alternate():
    spec = vfit.lookup("youtube:shorts")[2]
    assert vfit.aspect_matches(spec, 1080, 1920) == "primary"
    assert vfit.aspect_matches(spec, 1080, 1080) == "alternate"  # square accepted
    assert vfit.aspect_matches(spec, 1920, 1080) is None


def test_plan_noop_when_already_correct():
    p = vfit.plan({"width": 1080, "height": 1920, "duration": 5.0,
                   "file_size": 1000, "container": "mp4", "vcodec": "h264"},
                  "tiktok:feed")
    assert p["strategy"] == "noop"


def test_plan_defaults_to_pad_never_crop():
    p = vfit.plan(info4x3(), "tiktok:feed")
    assert p["strategy"] == "pad"
    assert "nothing is cut" in p["reason"]


def test_pad_builder_keeps_whole_frame():
    p = vfit.plan(info4x3(), "tiktok:feed")
    argv = vfit.build_fit("/tmp/in.mp4", "/tmp/out.mp4", p, strict=False)
    joined = " ".join(argv)
    assert "boxblur" in joined  # blurred-fill pad, not a destructive crop
    assert "overlay=(W-w)/2:(H-h)/2" in joined


def test_crop_refused_without_focus():
    with pytest.raises(ValueError, match="focus"):
        vfit.plan(info4x3(), "tiktok:feed", crop=True)


def test_crop_box_math_focus_top():
    # 640x480 (4:3) -> 1080x1920 (9:16): cover factor max(1080/640, 1920/480)
    # = 4.0 -> scaled 2560x1920; focus top => ox=(2560-1080)*0.5=740, oy=0
    SW2, SH2, ox, oy = vfit.crop_box(640, 480, 1080, 1920, 0.5, 0.0)
    assert (SW2, SH2, ox, oy) == (2560, 1920, 740, 0)


def test_crop_box_math_focus_center():
    SW2, SH2, ox, oy = vfit.crop_box(640, 480, 1080, 1920, 0.5, 0.5)
    assert (SW2, SH2) == (2560, 1920)
    assert ox == 740 and oy == 0  # no vertical excess: nothing cut top/bottom


def test_crop_plan_reports_what_gets_cut():
    p = vfit.plan(info4x3(), "tiktok:feed", crop=True, focus="center")
    assert p["strategy"] == "crop"
    rep = p["crop"]
    assert rep["lost_pct"] > 0
    assert "left" in rep["summary"] and "right" in rep["summary"]
    argv = vfit.build_fit("/tmp/in.mp4", "/tmp/out.mp4", p, strict=False)
    assert "crop=1080:1920:740:0" in " ".join(argv)


def test_focus_face_falls_back_without_cv2():
    if vfit.has_face_detection():
        pytest.skip("cv2 present — fallback path not exercised")
    (fx, fy), warnings = vfit.resolve_focus("face", input_path="/tmp/x.mp4")
    assert (fx, fy) == (0.5, 0.5)
    assert any("opencv" in w.lower() for w in warnings)


def test_noop_build_raises():
    p = vfit.plan({"width": 1080, "height": 1920, "duration": 5.0,
                   "file_size": 1000, "container": "mp4", "vcodec": "h264"},
                  "tiktok:feed")
    with pytest.raises(ValueError, match="noop"):
        vfit.build_fit("/tmp/in.mp4", "/tmp/out.mp4", p, strict=False)


def test_preflight_pass_and_fail():
    good = {"width": 1080, "height": 1920, "duration": 30.0,
            "file_size": 50 * 1024 * 1024, "container": "mp4", "vcodec": "h264"}
    res = vfit.preflight(good, "youtube:shorts")
    assert res["passed"], res["checks"]

    bad = dict(good, width=1920, height=1080)  # 16:9 into a 9:16 slot
    res = vfit.preflight(bad, "youtube:shorts")
    assert not res["passed"]
    aspect = next(c for c in res["checks"] if c["name"] == "aspect")
    assert not aspect["ok"]
    assert any("video fit" in f for f in res["fixes"])


def test_preflight_duration_and_size_fail():
    long = {"width": 1080, "height": 1920, "duration": 200.0,
            "file_size": 50 * 1024 * 1024, "container": "mp4", "vcodec": "h264"}
    res = vfit.preflight(long, "youtube:shorts")
    assert not res["passed"]
    assert "duration" in {c["name"] for c in res["checks"] if not c["ok"]}
    big = {"width": 1080, "height": 1920, "duration": 30.0,
           "file_size": 300 * 1024 * 1024, "container": "mp4", "vcodec": "h264"}
    res = vfit.preflight(big, "tiktok:feed")  # 287 MB cap
    assert not res["passed"]
    assert "file_size" in {c["name"] for c in res["checks"] if not c["ok"]}


def test_to_vertical_routes_through_pad():
    argv = vff.build_to_vertical("/tmp/in.mp4", "/tmp/out.mp4", strict=False)
    assert "boxblur" in " ".join(argv)
