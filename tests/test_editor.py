"""Tests for the editor/ module (AI Video Editor Worker). Pure builder tests
run without ffmpeg; a few integration tests run only if ffmpeg exists."""

import json
import os
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from editor import grading, kdenlive, shotcut, subtitles, highlights, broll
from editor import motion, branding, batch, qa, thumbnails, camera, compress
from video import ffmpeg as vff

FFMPEG = shutil.which("ffmpeg")
needs_ffmpeg = pytest.mark.skipif(not FFMPEG, reason="ffmpeg not installed")


# ---------------------------------------------------------------- grading --
def test_grade_list_has_all_presets():
    names = grading.list_grades()
    for want in ("teal-noir", "neon-city", "teal-street", "warm-vintage",
                 "noir", "blockbuster", "clean"):
        assert want in names


def test_teal_noir_filtergraph_matches_reference_look():
    fg = grading.filtergraph("teal-noir")
    assert "colorbalance" in fg
    # teal shadows: red down, blue up in shadows
    assert "rs=-0.25" in fg and "bs=0.25" in fg
    # warm highlights: red up
    assert "rh=0.05" in fg
    assert "vignette" in fg


def test_clean_is_passthrough():
    assert "colorbalance" not in grading.filtergraph("clean")


def test_unknown_grade_rejected():
    with pytest.raises(ValueError):
        grading.filtergraph("vaporwave-99")


# --------------------------------------------------------------- kdenlive --
def test_kdenlive_project_xml_roundtrip(tmp_path):
    p = kdenlive.Project(title="t", profile="1080p30")
    aid = p.add_asset("/tmp/a.mp4")
    cid = p.add_clip(aid, track="v1", in_s=1.0, out_s=5.0)
    p.add_effect(cid, "lift-gamma-gain", {"gain": "1.1"})
    p.add_marker(2.0, "hook")
    out = str(tmp_path / "t.kdenlive")
    p.save(out)
    xml = open(out, encoding="utf-8").read()
    assert "<mlt" in xml and "lift_gamma_gain" in xml
    assert os.path.exists(out + ".autosave")
    assert p.missing_media() == ["/tmp/a.mp4"]


def test_kdenlive_refuses_audio_on_video_track():
    p = kdenlive.Project()
    aid = p.add_asset("/tmp/a.mp3")
    with pytest.raises(ValueError):
        p.add_clip(aid, track="v1")


def test_kdenlive_unknown_effect_rejected():
    p = kdenlive.Project()
    aid = p.add_asset("/tmp/a.mp4")
    cid = p.add_clip(aid)
    with pytest.raises(ValueError):
        p.add_effect(cid, "lens-flare-9000")


def test_kdenlive_bad_profile_rejected():
    with pytest.raises(ValueError):
        kdenlive.Project(profile="imax70")


# ---------------------------------------------------------------- shotcut --
def test_shotcut_project_xml(tmp_path):
    p = shotcut.Project(title="s")
    aid = p.add_asset("/tmp/a.mp4")
    p.add_clip(aid, track="v1", in_s=0, out_s=4)
    out = str(tmp_path / "s.mlt")
    p.save(out)
    xml = open(out, encoding="utf-8").read()
    assert "shotcut" in xml and "<tractor" in xml


# --------------------------------------------------------------- subtitles --
def test_srt_roundtrip(tmp_path):
    cues = [{"start": 1.0, "end": 2.5, "text": "hello world"},
            {"start": 3.0, "end": 4.0, "text": "second line"}]
    p = str(tmp_path / "t.srt")
    subtitles.write_srt(cues, p)
    back = subtitles.parse_srt(p)
    assert len(back) == 2 and back[0]["text"] == "hello world"
    assert back[0]["start"] == pytest.approx(1.0)


def test_srt_validate_flags_problems():
    cues = [{"n": 1, "start": 0, "end": 5, "text": "x" * 100},
            {"n": 2, "start": 4, "end": 6, "text": "overlap"}]
    issues = subtitles.validate(cues)
    assert any("overlaps" in i for i in issues)
    assert any("too long" in i for i in issues)


def test_karaoke_ass_has_word_tags():
    ass = subtitles.karaoke_ass([{"start": 0, "end": 2,
                                  "text": "one two three four five"}])
    assert "\\k" in ass and "Dialogue" in ass


def test_heuristic_srt_distributes_over_speech(tmp_path):
    tr = tmp_path / "words.txt"
    tr.write_text("alpha beta gamma delta epsilon zeta")
    out = str(tmp_path / "o.srt")
    # speech only in 10..20 of a 30s timeline
    subtitles.heuristic_srt(str(tr), 30.0, [(0, 10), (20, 30)], out)
    cues = subtitles.parse_srt(out)
    assert cues and all(c["start"] >= 10.0 for c in cues)
    assert " ".join(c["text"] for c in cues).split() == \
        "alpha beta gamma delta epsilon zeta".split()


def test_burn_in_builder_args(tmp_path):
    argv = subtitles.build_burn_in("/tmp/in.mp4", "/tmp/out.mp4",
                                   "/tmp/c.srt", style="pop", strict=False)
    joined = " ".join(argv)
    assert "subtitles=" in joined and "libx264" in joined


# -------------------------------------------------------------- highlights --
def test_find_highlights_ranks_loudest_window():
    analysis = {"duration": 10.0,
                "energy_curve": [0.1] * 4 + [0.9] * 3 + [0.1] * 3,
                "scene_cuts": [], "silence_spans": []}
    hl = highlights.find_highlights(analysis, top_n=2)
    assert hl
    top = hl[0]
    # loudest window must cover the 4-7s loud region
    assert top["start"] <= 4.0 <= top["end"]


def test_find_highlights_empty_on_zero_duration():
    assert highlights.find_highlights({"duration": 0}) == []


# ------------------------------------------------------------------ broll --
def test_broll_plan_from_silence_gaps():
    analysis = {"silence_spans": [(2.0, 5.0), (8.0, 9.0)],
                "scene_cuts": [], "duration": 12.0}
    plan = broll.plan(analysis, ["b1.mp4", "b2.mp4"], mode="pip")
    assert len(plan["items"]) == 1  # only the >=1.5s gap
    assert plan["items"][0]["at"] == 2.0


def test_broll_pip_builder(tmp_path):
    plan = {"mode": "pip", "items": [
        {"at": 1.0, "duration": 2.0, "file": "/tmp/b.mp4",
         "mode": "pip", "position": "bottom-right", "pip_scale": 0.3}]}
    argv = broll.build_apply_pip("/tmp/in.mp4", "/tmp/out.mp4", plan,
                                 strict=False)
    joined = " ".join(argv)
    assert "overlay" in joined and "between(t,1.0,3.0)" in joined


# ----------------------------------------------------------------- motion --
def test_lower_third_renders(tmp_path):
    pytest.importorskip("PIL")
    out = str(tmp_path / "lt.png")
    p = motion.lower_third("Nova", subtext="AI Lab", output=out)
    assert os.path.exists(p) and os.path.getsize(p) > 1000


def test_text_card_renders(tmp_path):
    pytest.importorskip("PIL")
    out = str(tmp_path / "card.png")
    motion.text_card("Hello World", output=out)
    assert os.path.exists(out)


def test_emoji_caption_wrapper():
    assert motion.animated_caption_emoji("watch this") == "🔥 watch this 🔥"


# --------------------------------------------------------------- branding --
def test_brand_kit_roundtrip(tmp_path):
    home = str(tmp_path)
    branding.create(home, "ch1")
    kit = branding.load(home, "ch1")
    assert kit["grade"] == "teal-noir"
    assert kit["colors"]["bg"] == [8, 12, 16]
    assert "ch1" in branding.list_kits(home)


def test_brand_build_apply_embeds_grade_and_logo(tmp_path):
    pytest.importorskip("PIL")
    logo = str(tmp_path / "logo.png")
    from PIL import Image
    Image.new("RGBA", (100, 100), (255, 0, 0, 255)).save(logo)
    home = str(tmp_path)
    branding.create(home, "lg")
    kit = branding.load(home, "lg")
    kit["logo"] = logo
    argv = branding.build_apply("/tmp/in.mp4", "/tmp/out.mp4", kit,
                                strict=False)
    joined = " ".join(argv)
    assert "colorbalance" in joined  # teal-noir grade
    assert logo in joined           # watermark input


# ------------------------------------------------------------------ batch --
def test_queue_add_run_resume(tmp_path):
    home = str(tmp_path)
    batch.queue_add(home, "j1", ["echo", "hi"])
    batch.queue_add(home, "j2", ["false"], retries=2)
    res = batch.queue_run(home, dry_run=True)
    assert all(r["state"] == "done" for r in res)
    # real run: j2 fails -> retry-queued, then resume exhausts retry budget
    # (dry-run counted as attempt 1, so retries=2 gives one real retry)
    res = batch.queue_run(home)
    states = {r["job"]: r["state"] for r in res}
    assert states["j1"] == "done" and states["j2"] == "retry-queued"
    res = batch.queue_run(home, resume=True)
    states = {r["job"]: r["state"] for r in res}
    assert states["j1"] == "done"  # skipped, not re-run
    assert states["j2"] == "failed"  # retry budget exhausted


def test_batch_builder_grade(tmp_path):
    src = tmp_path / "a.mp4"
    src.write_bytes(b"x")
    out = tmp_path / "out"
    res = batch.run_batch(str(tmp_path), "grade", [str(tmp_path / "*.mp4")],
                          str(out), dry_run=True, look="noir")
    assert len(res["ok"]) == 1 and not res["failed"]


# --------------------------------------------------------------------- qa --
@needs_ffmpeg
def test_qa_flags_black_frames(tmp_path):
    black = str(tmp_path / "black.mp4")
    import subprocess
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "color=black:duration=2:size=320x240:rate=15",
                    "-c:v", "libx264", black], check=True)
    res = qa.verify(black)
    assert not res["passed"]
    assert any("black" in i for i in res["issues"])


@needs_ffmpeg
def test_qa_passes_clean_video(tmp_path):
    vid = str(tmp_path / "ok.mp4")
    import subprocess
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=15",
                    "-c:v", "libx264", vid], check=True)
    res = qa.verify(vid)
    assert res["passed"], res["issues"]


def test_verify_or_rerender_retries_once(tmp_path):
    vid = str(tmp_path / "v.mp4")
    calls = []
    real_verify = qa.verify
    seq = [{"passed": False, "issues": ["x"], "details": {}},
           {"passed": True, "issues": [], "details": {}}]
    qa.verify = lambda *a, **k: seq.pop(0)
    try:
        res = qa.verify_or_rerender(vid, lambda: calls.append(1))
    finally:
        qa.verify = real_verify
    assert res["passed"] and res["rerendered"] and calls == [1]


# ------------------------------------------------------------- thumbnails --
def test_contrast_ratio_math():
    ok, ratio = thumbnails.contrast_ok((0, 0, 0), (255, 255, 255))
    assert ok and ratio > 15
    ok2, _ = thumbnails.contrast_ok((200, 200, 200), (255, 255, 255))
    assert not ok2


# ----------------------------------------------------------------- camera --
def test_stabilize_builder_two_pass():
    passes = camera.build_stabilize("/tmp/in.mp4", "/tmp/out.mp4",
                                    strict=False)
    assert len(passes) == 2
    assert "vidstabdetect" in " ".join(passes[0])
    assert "vidstabtransform" in " ".join(passes[1])


def test_enhance_builder():
    argv = camera.build_enhance("/tmp/in.mp4", "/tmp/out.mp4",
                                denoise="strong", temp="warm", strict=False)
    joined = " ".join(argv)
    assert "hqdn3d=5:5:10:10" in joined


# --------------------------------------------------------------- compress --
def test_crf_ladder_values():
    argv = compress.build_crf("/tmp/in.mp4", "/tmp/o.mp4", codec="h264",
                              quality="high", strict=False)
    assert "-crf" in argv and "18" in argv
    argv = compress.build_crf("/tmp/in.mp4", "/tmp/o.mp4", codec="av1",
                              quality="small", strict=False)
    assert "libsvtav1" in argv


def test_export_builder_resolutions():
    argv, meta = vff.build_export("/tmp/in.mp4", "/tmp/o.mp4",
                                  resolution="4k", codec="hevc", strict=False)
    joined = " ".join(argv)
    assert "scale=-2:2160" in joined
    assert meta["codec"] == "hevc" and meta["resolution"] == "4k"


def test_export_rejects_unknown_resolution():
    with pytest.raises(ValueError):
        vff.build_export("/tmp/in.mp4", "/tmp/o.mp4", resolution="12k",
                         strict=False)
