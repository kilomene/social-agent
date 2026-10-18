"""Tests for video/pipeline/ (Toonflow core model port).

Real-execution tests are skipped when ffmpeg is absent; pure-function
tests always run. Uses the `home` fixture (tmp SOCIAL_AGENT_HOME).
"""

import json
import os
import sys
import threading

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from video import ffmpeg as vff
from video.pipeline import definition as d
from video.pipeline import nodes as nodes_mod
from video.pipeline import providers as providers_mod
from video.pipeline.providers import base as provider_base
from video.pipeline import qc as qc_mod
from video.pipeline import runner as runner_mod
from video.pipeline import script as script_mod
from video.pipeline import state as state_mod

FFMPEG = vff.which_ffmpeg()
needs_ffmpeg = pytest.mark.skipif(not FFMPEG, reason="ffmpeg not installed")

MAYA_BLOCK = (
    "Maya is a Black teenage girl, sixteen years old, with dark brown skin "
    "and long braids threaded with small amber beads that click when she "
    "moves. She carries a worn sketchbook in her left hand everywhere she "
    "goes. Her uniform is an oversized denim jacket over faded band tees, "
    "paint-stained jeans, and sneakers. She walks like she is casing every "
    "room before she enters it, shoulders angled, eyes drawing. She speaks "
    "in short clipped sentences with dry humor, a warm mid-range teen voice "
    "that never rises even when she is angry. Observant, stubborn, she draws "
    "what she cannot say. Her new-girl armor is sarcasm first and slow "
    "trust. Her emotional baseline is guarded; she rarely shows enthusiasm "
    "openly. Her goal is to belong somewhere. Her fear is becoming invisible "
    "like she felt in her old city. Her secret: she saw her own death in a "
    "vision and told no one.")

JONAH_BLOCK = (
    "Jonah is a Latino teenage boy, seventeen, warm tan skin, curly black "
    "hair, an easy grin that does not reach his eyes when the lake comes up. "
    "He wears a diner apron over flannel shirts and worn sneakers; he works "
    "at his family's diner. He is the skeptic who jokes through fear and "
    "stays fiercely loyal once you are his. He speaks laid-back with a "
    "slight rasp, unhurried, funny when he is nervous. His goal is to get "
    "out of Hollow Pines. His fear is ending up like his uncle Daniel, who "
    "disappeared twenty years ago. His secret: he touched the lake once at "
    "fourteen and has never told anyone what he saw. On screen he wipes "
    "tables, carries trays, leans on counters, always watching the door.")

SCRIPT_TEXT = """# E99 "Smoke Test"

**SCENE 1 — EXT. MIRROR LAKE — NIGHT**
*Black water. A girl's hand touches the surface.*

MAYA: (V.O.) It was waiting for me.

**SCENE 2 — INT. DINER — DAY**
*Jonah wipes the counter.*

JONAH: New girl gets the new-girl special.
MAYA: Generous.
"""

BIBLE_TEXT = """# Character Bible

**MAYA OKORO — 16, protagonist**
- Appearance: Black girl, dark brown skin, long braids with amber beads.

**JONAH REYES — 17**
- Appearance: Latino boy, warm tan skin, curly black hair.
"""

REVIEW = {"watermark_free": True, "identity_match": True,
          "artifacts": "none", "reviewer": "smoke-test"}


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


@pytest.fixture
def proj(tmp_path):
    """GATE-A-ready fixture project dir."""
    p = str(tmp_path / "proj")
    _write(os.path.join(p, "CHARACTER-BIBLE.md"), BIBLE_TEXT)
    _write(os.path.join(p, "voice-cast.json"), json.dumps({
        "MAYA": {"voice_id": "maya-teen-f-01", "locked": True},
        "JONAH": {"voice_id": "jonah-teen-m-02", "locked": True}}))
    _write(os.path.join(p, "identity-blocks", "MAYA.md"), MAYA_BLOCK)
    _write(os.path.join(p, "identity-blocks", "JONAH.md"), JONAH_BLOCK)
    _write(os.path.join(p, "identity-blocks", "hashes.json"), json.dumps({
        "MAYA": qc_mod.identity_block_hash(MAYA_BLOCK),
        "JONAH": qc_mod.identity_block_hash(JONAH_BLOCK)}))
    # minimal PNG (magic bytes satisfy the imghdr sniff)
    pdir = os.path.join(p, "assets", "portraits", "MAYA")
    os.makedirs(pdir, exist_ok=True)
    with open(os.path.join(pdir, "front.png"), "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    pdir = os.path.join(p, "assets", "portraits", "JONAH")
    os.makedirs(pdir, exist_ok=True)
    with open(os.path.join(pdir, "front.png"), "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    _write(os.path.join(p, "continuity", "ledger.md"),
           "# ledger\n- clue: bracelet D.R. planted E3\n")
    _write(os.path.join(p, "scripts", "e99.md"), SCRIPT_TEXT)
    return p


# ------------------------------------------------------------- definition ---
def test_typed_values_and_unresolved():
    v = d.typed_value("STRING", "hi")
    assert d.is_typed_value(v)
    assert d.is_unresolved(d.UNRESOLVED)
    assert not d.is_unresolved(v)
    with pytest.raises(ValueError):
        d.typed_value("INT", "not-an-int")
    with pytest.raises(ValueError):
        d.typed_value("VIDEO", {"url": "", "mimeType": "video/mp4"})
    with pytest.raises(ValueError):
        d.typed_value("VIDEO", {"url": "x.mp4", "mimeType": "image/png"})
    ref = d.input_ref("gen_shot_0", "clip")
    assert d.is_input_ref(ref)
    n = d.make_node("n1", "gen_shot", inputs={"clip": ref}, retries=3)
    assert n["status"] == d.IDLE and n["retries"] == 3


def test_redact_secrets():
    msg = d.redact_secrets("failed: apiKey=sk-abc123XYZ and token=abcdef")
    assert "sk-abc123XYZ" not in msg and "abcdef" not in msg
    assert "[REDACTED]" in msg


def test_advance_publish_state_machine():
    assert qc_mod.advance_publish_state("defined", "produced") == "produced"
    assert qc_mod.advance_publish_state("qc'd", "proposed") == "proposed"
    with pytest.raises(d.PipelineError):
        qc_mod.advance_publish_state("defined", "proposed")  # no skips
    with pytest.raises(d.PipelineError):
        qc_mod.advance_publish_state("aired", "defined")  # no rewind


# ----------------------------------------------------------------- script ---
def test_script_parses_scenes_and_dialogue():
    parsed = script_mod.parse_script(SCRIPT_TEXT)
    assert len(parsed["scenes"]) == 2
    assert parsed["scenes"][0]["location"] == "MIRROR LAKE"
    assert parsed["scenes"][1]["int_ext"] == "INT."
    assert len(parsed["dialogue"]) == 3
    assert parsed["dialogue"][0]["vo"] is True
    assert parsed["dialogue"][0]["character"] == "MAYA"
    assert script_mod.speaking_characters(parsed) == ["MAYA", "JONAH"]


def test_voice_filename_format():
    name = script_mod.voice_filename(1, 3, 7, "Maya Okoro", "maya-teen-f-01")
    assert name == "voice-audio/e01-s3d7_MAYA-maya-teen-f-01.wav"


# -------------------------------------------------------------- providers ---
def test_provider_registry_and_contract():
    provs = providers_mod.list_providers()
    ids = [p.id for p in provs]
    assert "local-ffmpeg" in ids and "muse-video" in ids
    local = providers_mod.get_provider("local-ffmpeg")
    assert local.rules == [] and len(local.models) == 3
    assert local.has("generate_video")
    assert local.has("generate_image")
    assert local.has("generate_audio")
    with pytest.raises(d.PipelineError):
        providers_mod.get_provider("nope")
    free = [p.id for p in providers_mod.free_providers()]
    assert "local-ffmpeg" in free and "muse-video" not in free


def test_stub_providers_raise_honest_blocks():
    muse = providers_mod.get_provider("muse-video")
    assert muse.has("generate_video")
    with pytest.raises(d.PipelineBlockedError) as ei:
        muse.generate_video(None, {"prompt": "x"})
    assert "region gate 403" in str(ei.value)
    tts = providers_mod.get_provider("tts-stub")
    with pytest.raises(d.PipelineBlockedError) as ei2:
        tts.generate_audio(None, {"text": "hello"})
    assert "no $0 provider" in str(ei2.value)


def test_local_ffmpeg_rejects_non_lavfi():
    local = providers_mod.get_provider("local-ffmpeg")
    with pytest.raises(d.PipelineBlockedError):
        local.generate_video(provider_base.ProviderContext({}),
                             {"prompt": "a lake at night"})


@needs_ffmpeg
def test_generate_media_host_flow(tmp_path):
    local = providers_mod.get_provider("local-ffmpeg")
    out_dir = str(tmp_path / "gen")
    assets = provider_base.generate_media(
        local, "video",
        {"prompt": "test", "other": {"lavfi": "testsrc=size=320x180:rate=10",
                                    "duration_s": 2}},
        out_dir)
    assert len(assets) == 1
    assert os.path.exists(assets[0]["url"])
    assert assets[0]["mimeType"] == "video/mp4"
    assert assets[0]["url"].startswith(out_dir)


@needs_ffmpeg
def test_generate_media_cleans_up_on_error(tmp_path):
    class Boom(provider_base.ProviderDefinition):
        id = "boom"
        label = "boom"
        rules = []
        models = [{"id": "m", "label": "m", "type": "video"}]

        def generate_video(self, ctx, request):
            return [{"mediaType": "video",
                     "data": b"\x00" * 10, "mimeType": "video/mp4"},
                    {"mediaType": "bogus"}]  # second asset invalid

    out_dir = str(tmp_path / "gen")
    with pytest.raises(d.ProviderError):
        provider_base.generate_media(Boom(), "video", {"prompt": "x"},
                                     out_dir)
    leftovers = os.listdir(out_dir) if os.path.exists(out_dir) else []
    assert leftovers == []


# ------------------------------------------------------------------ state ---
def test_state_create_resume_and_atomicity(home):
    st = state_mod.EpisodeState(home, "e99")
    nodes = [d.make_node("a", "parse_script"),
             d.make_node("b", "gate_a", deps=["a"])]
    ep = d.make_episode("e99", "t", "/tmp/proj", nodes)
    ep["publish_state"] = "defined"
    st.create(ep)
    assert os.path.exists(os.path.join(st.dir, "state.json"))
    # atomic: file is complete JSON, no tmp leftovers
    assert not [f for f in os.listdir(st.dir) if f.startswith(".tmp-")]

    st2 = state_mod.EpisodeState(home, "e99")
    doc = st2.load()
    assert doc["nodes"][0]["status"] == d.IDLE

    # simulate a succeeded node, then resume re-reads its outputs
    out = {"x": d.typed_value("STRING", "done")}
    st2.set_node("a", status=d.SUCCEEDED, outputs=out)
    assert st2.succeeded_outputs("a") == out
    assert [n["id"] for n in st2.ready_nodes()] == ["b"]

    st2.set_node("a", status=d.FAILED)
    assert [n["id"] for n in st2.blocked_nodes()] == ["b"]

    st2.reset_node("b", reason="test")
    assert st2.node("b")["status"] == d.IDLE


# --------------------------------------------------------------------- qc ---
def test_gate_a_passes_on_fixture(proj):
    parsed = script_mod.parse_script(SCRIPT_TEXT)
    result = qc_mod.gate_a(proj, parsed, episode_no=99)
    assert result["passed"], json.dumps(result["failed"], indent=2)


def test_gate_a_fails_without_voice_cast(proj):
    os.unlink(os.path.join(proj, "voice-cast.json"))
    parsed = script_mod.parse_script(SCRIPT_TEXT)
    result = qc_mod.gate_a(proj, parsed)
    assert not result["passed"]
    assert "voice_cast_locked" in result["failed"]


def test_gate_a_fails_on_short_identity_block(proj):
    _write(os.path.join(proj, "identity-blocks", "MAYA.md"), "too short")
    parsed = script_mod.parse_script(SCRIPT_TEXT)
    result = qc_mod.gate_a(proj, parsed)
    assert not result["passed"]
    assert "identity_blocks_verbatim" in result["failed"]


def test_gate_b_rejects_hash_mismatch_without_ffmpeg(tmp_path):
    clip = str(tmp_path / "clip.mp4")
    with open(clip, "wb") as fh:
        fh.write(b"\x00")
    result = qc_mod.gate_b_shot(
        clip, expected_identity_hash="aaa", actual_identity_hash="bbb",
        core_look_present=True, review=REVIEW)
    assert not result["passed"]
    assert "identity_block_hash_match" in result["failed"]
    assert "corrective" in result and "ALONE" in result["corrective"]


def test_next_air_slot():
    from zoneinfo import ZoneInfo
    # Sat 2026-10-17 16:50 EDT -> next slot Sun 2026-10-18 15:00 EDT
    now = __import__("datetime").datetime(
        2026, 10, 17, 16, 50, tzinfo=ZoneInfo("America/New_York"))
    slot = qc_mod.next_air_slot(now)
    assert (slot.weekday(), slot.hour, slot.day) == (6, 15, 18)


# ----------------------------------------------------------------- runner ---
def _define(home, proj, episode_id, shots, provider):
    st = state_mod.EpisodeState(home, episode_id)
    nodes = nodes_mod.build_initial_nodes(
        script_path="scripts/e99.md", shots=shots, provider=provider,
        episode_no=99)
    ep = d.make_episode(episode_id, "smoke", proj, nodes,
                        script_path="scripts/e99.md", provider=provider)
    ep["publish_state"] = "defined"
    st.create(ep)
    return st


def _shots():
    return [{"id": "S1", "character": "MAYA",
             "prompt": "EXT lake night, a girl's hand touches black water",
             "other": {"lavfi": "testsrc=size=1280x720:rate=24",
                       "duration_s": 3}},
            {"id": "S2", "character": "JONAH",
             "prompt": "INT diner day, a teen wipes the counter",
             "other": {"lavfi": "testsrc=size=1280x720:rate=24",
                       "duration_s": 3}}]


def test_runner_stub_provider_blocks_honestly(home, proj):
    _define(home, proj, "e-stub", _shots(), "muse-video")
    result = runner_mod.run(home, "e-stub", episode_no=99, review=REVIEW)
    assert result["completed"] is False
    assert result["failed"] == ["gen_shot_0", "gen_shot_1"]
    st = state_mod.EpisodeState(home, "e-stub")
    node = st.node("gen_shot_0")
    assert node["status"] == d.FAILED
    assert node["attempts"] == 1  # sentinel: no retry
    assert "region gate 403" in node["error"]
    assert st.node("gen_shot_1")["status"] == d.FAILED  # each shot alone
    # head nodes succeeded and were NOT restarted
    assert st.node("parse_script")["status"] == d.SUCCEEDED


def test_runner_resume_skips_succeeded(home, proj):
    _define(home, proj, "e-resume", _shots(), "muse-video")
    runner_mod.run(home, "e-resume", episode_no=99, review=REVIEW)
    st = state_mod.EpisodeState(home, "e-resume")
    before = st.node("parse_script")["attempts"]
    # reset the blocked node and re-run: head nodes must be skipped
    st.reset_node("gen_shot_0", reason="test retry")
    runner_mod.run(home, "e-resume", episode_no=99, review=REVIEW)
    st2 = state_mod.EpisodeState(home, "e-resume")
    assert st2.node("parse_script")["attempts"] == before
    assert st2.node("gen_shot_0")["attempts"] == 1


def test_runner_cooperative_cancel(home, proj):
    _define(home, proj, "e-cancel", _shots(), "muse-video")
    cancelled = threading.Event()
    cancelled.set()
    with pytest.raises(d.CancelledError):
        runner_mod.run(home, "e-cancel", episode_no=99, review=REVIEW,
                       cancelled=cancelled)


@needs_ffmpeg
def test_runner_full_local_path_blocks_at_gate_c_on_tts(home, proj):
    """local-ffmpeg: shots generate + pass GATE B; assemble honestly fails
    GATE C (no $0 TTS) — the expected $0-budget outcome."""
    _define(home, proj, "e-local", _shots(), "local-ffmpeg")
    result = runner_mod.run(home, "e-local", episode_no=99, review=REVIEW)
    st = state_mod.EpisodeState(home, "e-local")
    assert st.node("gen_shot_0")["status"] == d.SUCCEEDED
    assert st.node("qc_shot_0")["status"] == d.SUCCEEDED
    assert result["failed"] == ["assemble"]
    err = st.node("assemble")["error"]
    assert "GATE C failed" in err
    assert "every_line_has_locked_tts" in err
    # assembly.mp4 was really concatenated before the gate ran
    assert os.path.exists(os.path.join(st.dir, "assembly.mp4"))


@needs_ffmpeg
def test_gate_b_passes_for_synthetic_clip(home, proj):
    from video.pipeline.providers import base as pb
    local = providers_mod.get_provider("local-ffmpeg")
    out_dir = os.path.join(home, "gen")
    assets = pb.generate_media(
        local, "video",
        {"prompt": "x", "other": {"lavfi": "testsrc=size=1280x720:rate=24",
                                  "duration_s": 3}}, out_dir)
    clip = assets[0]["url"]
    h = qc_mod.identity_block_hash(MAYA_BLOCK)
    result = qc_mod.gate_b_shot(clip, h, h, True, review=REVIEW)
    assert result["passed"], json.dumps(result["failed"], indent=2)


def test_propose_publish_handoff(home, tmp_path):
    from approvals import queue as q
    meta_path = str(tmp_path / "metadata.json")
    _write(meta_path, json.dumps({"title": "T", "description": "D"}))
    st = state_mod.EpisodeState(home, "e-pub")
    node = d.make_node(
        "propose_publish", "propose_publish",
        params={"platform": "youtube", "account": "Nova Automation",
                "master_path": "/tmp/master.mp4"},
        inputs={"metadata": d.typed_value(
            "FILE", {"url": meta_path, "mimeType": "application/json"})},
        retries=0)
    ep = d.make_episode("e-pub", "t", "/tmp", [node], provider="local-ffmpeg")
    ep["publish_state"] = "qc'd"
    st.create(ep)
    result = runner_mod.run(home, "e-pub")
    assert result["completed"] is True
    items = q.list_items(home)
    assert len(items) == 1
    item = items[0]
    assert item["type"] == "post_video"
    assert item["status"] == "pending"  # never auto-approved
    assert item["ref"] == {"store": "video_pipeline/episodes.json",
                           "id": "e-pub"}
    assert item["payload"]["file"] == "/tmp/master.mp4"
    st2 = state_mod.EpisodeState(home, "e-pub")
    assert st2.doc()["publish_state"] == "proposed"
