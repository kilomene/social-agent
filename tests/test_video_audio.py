"""Tests for video/ and audio/ modules.

Real-execution tests are skipped when ffmpeg is absent; command-builder
tests always run (builders are pure functions).
"""

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video import ffmpeg as vff
from video import plans as vplans
from audio import clips as audio_mod

FFMPEG = vff.which_ffmpeg()
needs_ffmpeg = pytest.mark.skipif(not FFMPEG, reason="ffmpeg not installed")


def _make_fixtures(tmp_path):
    mp4 = str(tmp_path / "in.mp4")
    mp3 = str(tmp_path / "in.mp3")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc=duration=4:size=640x480:rate=30",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", mp4],
        check=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "sine=frequency=880:duration=10",
         "-c:a", "libmp3lame", "-b:a", "192k", mp3], check=True)
    return mp4, mp3


# ----------------------------------------------------------- builders ---

@pytest.fixture
def dummy(tmp_path):
    """Placeholder input files so builders' existence guards pass."""
    a = tmp_path / "a.mp4"
    b = tmp_path / "a.mp3"
    vo = tmp_path / "vo.mp3"
    for f in (a, b, vo):
        f.write_bytes(b"\x00")
    return str(a), str(b), str(vo)


def test_build_clip_args(dummy):
    mp4, _, _ = dummy
    argv = vff.build_clip(mp4, "b.mp4", 1, 2)
    assert argv[:4] == ["ffmpeg", "-y", "-ss", "1"]
    assert "-t" in argv and "2" in argv and argv[-1] == "b.mp4"


def test_build_clip_fades_audio(dummy):
    _, mp3, _ = dummy
    argv = audio_mod.build_clip(mp3, "b.mp3", 5, 10, fade_in=1, fade_out=2)
    af = argv[argv.index("-af") + 1]
    assert "afade=t=in" in af and "afade=t=out" in af


def test_build_concat_needs_two(dummy):
    mp4, _, _ = dummy
    with pytest.raises(ValueError):
        vff.build_concat([mp4], "out.mp4")


def test_build_to_vertical_filter(dummy):
    mp4, _, _ = dummy
    argv = vff.build_to_vertical(mp4, "b.mp4")
    vf = argv[argv.index("-vf") + 1]
    assert "1080:1920" in vf and "boxblur" in vf and "overlay" in vf


def test_build_compress_presets(dummy):
    mp4, _, _ = dummy
    argv = vff.build_compress(mp4, "b.mp4", "youtube")
    assert "12M" in argv and "youtube" in vff.PRESETS
    with pytest.raises(ValueError):
        vff.build_compress(mp4, "b.mp4", "vine")


def test_build_mix_ducking_filter(dummy):
    _, bed, vo = dummy
    argv = audio_mod.build_mix(vo, bed, "out.mp3")
    fc = argv[argv.index("-filter_complex") + 1]
    assert "sidechaincompress" in fc and "[mixout]" in fc
    assert argv[argv.index("-map") + 1] == "[mixout]"


def test_build_normalize_preset(dummy):
    _, mp3, _ = dummy
    argv = audio_mod.build_normalize(mp3, "b.mp3", "podcast")
    assert "loudnorm=I=-16" in argv[argv.index("-af") + 1]


def test_refuses_overwrite(dummy):
    mp4, mp3, _ = dummy
    with pytest.raises(ValueError):
        vff.build_clip(mp4, mp4, 0, 1)
    with pytest.raises(ValueError):
        audio_mod.build_clip(mp3, mp3, 0, 1, 0, 0)


def test_missing_input():
    with pytest.raises(FileNotFoundError):
        vff.build_clip("/nope/missing.mp4", "b.mp4", 0, 1)


def test_plan_validation(tmp_path):
    with pytest.raises(ValueError):
        vplans.create(str(tmp_path), "bad", [{"op": "explode"}])
    plan = vplans.create(str(tmp_path), "p1",
                         [{"op": "clip", "start": 1, "duration": 2}])
    assert plan["name"] == "p1"
    assert vplans.list_plans(str(tmp_path)) == ["p1"]


# ------------------------------------------------------- real execution ---

@needs_ffmpeg
def test_video_info_real(tmp_path):
    mp4, _ = _make_fixtures(tmp_path)
    inf = vff.info(mp4)
    assert inf["width"] == 640 and inf["height"] == 480
    assert 3.5 < inf["duration"] < 4.5


@needs_ffmpeg
def test_video_clip_real(tmp_path):
    mp4, _ = _make_fixtures(tmp_path)
    out = str(tmp_path / "clip.mp4")
    vff.run_cmd(vff.build_clip(mp4, out, 1, 2))
    inf = vff.info(out)
    assert 1.5 < inf["duration"] < 2.5


@needs_ffmpeg
def test_video_to_vertical_real(tmp_path):
    mp4, _ = _make_fixtures(tmp_path)
    out = str(tmp_path / "vert.mp4")
    vff.run_cmd(vff.build_to_vertical(mp4, out))
    inf = vff.info(out)
    assert (inf["width"], inf["height"]) == (1080, 1920)


@needs_ffmpeg
def test_video_frame_real(tmp_path):
    mp4, _ = _make_fixtures(tmp_path)
    out = str(tmp_path / "frame.jpg")
    vff.run_cmd(vff.build_frame(mp4, out, at=1))
    assert os.path.getsize(out) > 1000


@needs_ffmpeg
def test_audio_clip_fades_real(tmp_path):
    _, mp3 = _make_fixtures(tmp_path)
    out = str(tmp_path / "aclip.mp3")
    audio_mod.run_cmd(audio_mod.build_clip(mp3, out, 2, 5, fade_in=1, fade_out=1))
    assert os.path.getsize(out) > 1000


@needs_ffmpeg
def test_audio_mix_real(tmp_path):
    _, mp3 = _make_fixtures(tmp_path)
    vo = str(tmp_path / "vo.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                    "-i", "sine=frequency=220:duration=4",
                    "-c:a", "libmp3lame", vo], check=True)
    out = str(tmp_path / "mix.mp3")
    audio_mod.run_cmd(audio_mod.build_mix(vo, mp3, out))
    assert os.path.getsize(out) > 1000


@needs_ffmpeg
def test_plan_run_real(tmp_path):
    mp4, _ = _make_fixtures(tmp_path)
    vplans.create(str(tmp_path), "p1", [
        {"op": "clip", "start": 0, "duration": 2},
        {"op": "to-vertical"},
    ])
    out = str(tmp_path / "final.mp4")
    vplans.run(str(tmp_path), "p1", mp4, out)
    inf = vff.info(out)
    assert (inf["width"], inf["height"]) == (1080, 1920)
