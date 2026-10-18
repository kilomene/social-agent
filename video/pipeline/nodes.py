"""Node executors for the episode DAG.

Each executor: fn(ctx, node, inputs) -> {output_name: typed_value}.
ctx carries home, episode state, cancel event, and logging. Inputs are
already resolved typed values (or UNRESOLVED). Generate functions return
FINAL media assets, never task IDs.
"""

from __future__ import annotations

import json
import os

from . import definition as d
from . import providers
from .providers import base as provider_base
from . import qc
from . import script as script_mod

# --- Core Look block (cinematic-effect-engine, 16:9 per standing rules) --------
CORE_LOOK_BLOCK = (
    "CORE LOOK: photorealistic live-action, premium streaming-original "
    "quality; natural skin texture and facial detail; physically plausible "
    "lighting motivated by a real in-scene source; rich color grade, deep "
    "blacks, natural highlight roll-off; subtle natural film grain; 16:9 "
    "edge-to-edge frame, no pillarbox/letterbox; film-like 24fps motion with "
    "natural motion blur; NO watermark, logo, text overlay, subtitle, or UI "
    "element in frame; no plastic skin, no warped hands/faces."
)


def _ep_dir(ctx):
    return ctx.state.dir


def _abs(ctx, rel):
    return rel if os.path.isabs(rel) else os.path.join(ctx.home, rel)


def _rel(ctx, path):
    ap = os.path.abspath(path)
    hp = os.path.abspath(ctx.home)
    if ap.startswith(hp + os.sep):
        return os.path.relpath(ap, hp)
    return ap


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


# --- node: parse_script ---------------------------------------------------------
def parse_script(ctx, node, inputs):
    params = node["params"]
    script_path = params.get("script_path") or ""
    if not os.path.isabs(script_path):
        script_path = os.path.join(ctx.episode["project_dir"], script_path)
    parsed = script_mod.parse_script_file(script_path)
    out_path = os.path.join(_ep_dir(ctx), "dialogue-inventory.json")
    _write_json(out_path, {"scenes": parsed["scenes"],
                           "dialogue": parsed["dialogue"]})
    return {
        "inventory": d.typed_value("FILE", {"url": _rel(ctx, out_path),
                                            "mimeType": "application/json"}),
        "scene_count": d.typed_value("INT", len(parsed["scenes"])),
        "dialogue_count": d.typed_value("INT", len(parsed["dialogue"])),
        "speakers": d.typed_value(
            "STRING", ",".join(script_mod.speaking_characters(parsed))),
    }


# --- node: gate_a -----------------------------------------------------------------
def gate_a(ctx, node, inputs):
    inv = inputs.get("inventory")
    if d.is_unresolved(inv):
        raise d.PipelineError("gate_a: dialogue inventory unresolved")
    with open(_abs(ctx, inv["value"]["url"]), encoding="utf-8") as fh:
        parsed = json.load(fh)
    result = qc.gate_a(ctx.episode["project_dir"], parsed,
                       episode_no=node["params"].get("episode_no", 1))
    out_path = os.path.join(_ep_dir(ctx), "gate-a.json")
    _write_json(out_path, result)
    if not result["passed"]:
        raise d.GateFailedError(
            "GATE A failed: " + "; ".join(
                f"{c['name']}: {c['detail']}" for c in result["checks"]
                if not c["passed"]))
    return {
        "verdict": d.typed_value("FILE", {"url": _rel(ctx, out_path),
                                          "mimeType": "application/json"}),
        "passed": d.typed_value("BOOLEAN", True),
    }


# --- node: plan_shots ---------------------------------------------------------------
def _parse_shot_plan_markdown(text):
    import re
    shots = []
    for line in text.splitlines():
        m = re.match(r"\s*[-*]\s*(C\d+|S\d+|SHOT\s*\d+)\s*:\s*(.+)$",
                     line, re.IGNORECASE)
        if m:
            shots.append({"id": m.group(1).upper().replace(" ", ""),
                          "prompt": m.group(2).strip()})
    return shots


def plan_shots(ctx, node, inputs):
    params = node["params"]
    shots = params.get("shots")
    if not shots:
        plan_path = params.get("shot_plan_path") or ""
        if not os.path.isabs(plan_path):
            plan_path = os.path.join(ctx.episode["project_dir"], plan_path)
        if not os.path.exists(plan_path):
            raise d.PipelineError(f"shot plan not found: {plan_path!r}")
        with open(plan_path, encoding="utf-8") as fh:
            shots = _parse_shot_plan_markdown(fh.read())
    if not shots:
        raise d.PipelineError("no shots defined (pass shots= or a shot plan)")
    for i, s in enumerate(shots):
        s.setdefault("id", f"S{i + 1}")
        if not s.get("prompt"):
            raise d.PipelineError(f"shot {s['id']}: empty prompt")
    out_path = os.path.join(_ep_dir(ctx), "shots.json")
    _write_json(out_path, {"shots": shots})
    return {
        "shots": d.typed_value("FILE", {"url": _rel(ctx, out_path),
                                        "mimeType": "application/json"}),
        "shot_count": d.typed_value("INT", len(shots)),
    }


# --- node: gen_shot -------------------------------------------------------------------
def _shot_prompt(shot, identity_block):
    parts = []
    if identity_block:
        parts.append(identity_block.strip())
    parts.append(CORE_LOOK_BLOCK)
    parts.append("SHOT: " + shot["prompt"])
    return "\n\n".join(parts)


def gen_shot(ctx, node, inputs):
    params = node["params"]
    shot = params["shot"]
    ctx.check_cancelled()
    provider = providers.get_provider(
        params.get("provider") or ctx.episode.get("provider") or "local-ffmpeg",
        cancelled=ctx.cancelled)
    identity_block = shot.get("identity_block", "") or params.get(
        "identity_block", "")
    identity_hash = (qc.identity_block_hash(identity_block)
                     if identity_block else "")
    request = {
        "prompt": _shot_prompt(shot, identity_block),
        "model": params.get("model") or "",
        "ratio": "16:9",
        "reference_paths": params.get("reference_paths") or [],
        "other": params.get("other") or {},
    }
    gen_dir = os.path.join(_ep_dir(ctx), "assets", "generated")
    assets = provider_base.generate_media(
        provider, "video", request, gen_dir, cancelled=ctx.cancelled)
    asset = assets[0]
    record = {
        "shot_id": shot["id"], "provider": provider.id,
        "model": request["model"],
        "identity_block_hash": identity_hash,
        "core_look_present": True,
        "prompt": request["prompt"],
        "asset": {"url": _rel(ctx, asset["url"]),
                  "mimeType": asset["mimeType"]},
    }
    rec_path = os.path.join(_ep_dir(ctx), "records",
                            f"gen-{shot['id']}.json")
    _write_json(rec_path, record)
    return {
        "clip": d.typed_value("VIDEO", {"url": _rel(ctx, asset["url"]),
                                        "mimeType": asset["mimeType"]}),
        "record": d.typed_value("FILE", {"url": _rel(ctx, rec_path),
                                         "mimeType": "application/json"}),
    }


# --- node: qc_shot --------------------------------------------------------------------
def qc_shot(ctx, node, inputs):
    clip = inputs.get("clip")
    record = inputs.get("record")
    if d.is_unresolved(clip) or d.is_unresolved(record):
        raise d.PipelineError("qc_shot: clip/record unresolved")
    with open(_abs(ctx, record["value"]["url"]), encoding="utf-8") as fh:
        rec = json.load(fh)
    result = qc.gate_b_shot(
        _abs(ctx, clip["value"]["url"]),
        expected_identity_hash=node["params"].get("expected_identity_hash",
                                                  rec.get("identity_block_hash")),
        actual_identity_hash=rec.get("identity_block_hash"),
        core_look_present=rec.get("core_look_present", False),
        review=node["params"].get("review"))
    out_path = os.path.join(_ep_dir(ctx), "records",
                            f"qc-{rec['shot_id']}.json")
    _write_json(out_path, result)
    if not result["passed"]:
        raise d.GateFailedError(
            f"GATE B rejected shot {rec['shot_id']}: "
            + result.get("corrective", "see verdict"))
    return {
        "verdict": d.typed_value("FILE", {"url": _rel(ctx, out_path),
                                          "mimeType": "application/json"}),
        "accepted_clip": clip,
    }


# --- node: assemble ---------------------------------------------------------------------
def assemble(ctx, node, inputs):
    """Concat accepted shots; build the mix manifest + assembly record;
    run GATE C. Failed shots regenerate ALONE (reset their gen node)."""
    ctx.check_cancelled()
    clips = []
    for name, val in sorted(inputs.items()):
        if name.startswith("clip_") and not d.is_unresolved(val):
            clips.append(_abs(ctx, val["value"]["url"]))
    if not clips:
        raise d.PipelineError("assemble: no accepted clips wired in")
    ep_dir = _ep_dir(ctx)
    assembly_path = os.path.join(ep_dir, "assembly.mp4")

    argv = None
    try:
        from video import ffmpeg as vff
        if not vff.which_ffmpeg():
            raise d.PipelineBlockedError(
                "assemble: ffmpeg binary not found on this host")
        # build_concat maps its filter outputs explicitly ([outv]/[outa]):
        # no ffmpeg default stream selection anywhere in this build.
        argv = vff.build_concat(clips, assembly_path)
        vff.run_cmd(argv)
    except d.PipelineBlockedError:
        raise
    except Exception as exc:
        raise d.PipelineError(f"assemble concat failed: {exc}") from exc

    # Four-layer mix manifest per scene (paths or explicit null).
    inv_path = os.path.join(ep_dir, "dialogue-inventory.json")
    dialogue = []
    if os.path.exists(inv_path):
        with open(inv_path, encoding="utf-8") as fh:
            dialogue = json.load(fh).get("dialogue", [])
    scenes = sorted({l["scene_no"] for l in dialogue})
    manifest = {"scenes": {
        str(s): {"dialogue": None, "foley": None,
                 "environment": None, "music": None} for s in scenes}}
    man_path = os.path.join(ep_dir, "mix-manifest.json")
    _write_json(man_path, manifest)
    ctx.advance_publish_state("produced")

    voice_cast = qc.load_voice_cast(ctx.episode["project_dir"])
    result = qc.gate_c({
        "master_path": assembly_path,
        "dialogue": dialogue,
        "episode_no": node["params"].get("episode_no", 1),
        "voice_cast": voice_cast,
        "voice_dir": os.path.join(ctx.episode["project_dir"], "voice-audio"),
        "mix_manifest": manifest,
        "assembly_argv": argv or [],
        "lipsync_report": node["params"].get("lipsync_report") or {},
        "score": node["params"].get("score") or {},
        "srt_path": node["params"].get("srt_path") or "",
        "dialogue_windows": node["params"].get("dialogue_windows") or [],
    })
    out_path = os.path.join(ep_dir, "gate-c.json")
    _write_json(out_path, result)
    if not result["passed"]:
        raise d.GateFailedError(
            "GATE C failed: " + "; ".join(
                f"{c['name']}: {c['detail']}" for c in result["checks"]
                if not c["passed"]))
    return {
        "assembly": d.typed_value("VIDEO", {"url": _rel(ctx, assembly_path),
                                            "mimeType": "video/mp4"}),
        "verdict": d.typed_value("FILE", {"url": _rel(ctx, out_path),
                                          "mimeType": "application/json"}),
    }


# --- node: finish -------------------------------------------------------------------------
def finish(ctx, node, inputs):
    """Branding/captions/upscale records, metadata package, GATE D."""
    ctx.check_cancelled()
    assembly = inputs.get("assembly")
    if d.is_unresolved(assembly):
        raise d.PipelineError("finish: assembly unresolved")
    ep_dir = _ep_dir(ctx)
    params = node["params"]

    # Final A/V mux with the literal explicit mapping (the AGENTS.md mux
    # gotcha): video input 0, final mixed audio input 1 — never ffmpeg's
    # default stream selection.
    final_audio = params.get("final_audio") or ""
    mux_argv = []
    muxed_path = ""
    if final_audio and os.path.exists(final_audio):
        from video import ffmpeg as vff
        if not vff.which_ffmpeg():
            raise d.PipelineBlockedError(
                "finish: ffmpeg binary not found on this host")
        muxed_path = os.path.join(ep_dir, "final-mux.mp4")
        mux_argv = ["ffmpeg", "-y", "-i", _abs(ctx, assembly["value"]["url"]),
                    "-i", final_audio,
                    "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", muxed_path]
        vff.run_cmd(mux_argv)
        _write_json(os.path.join(ep_dir, "final-mux.json"),
                    {"argv": mux_argv, "output": _rel(ctx, muxed_path)})

    # Metadata package (growth.youtube helpers — words, not pixels).
    from growth import youtube as yt
    title = params.get("title") or ctx.episode.get("title", "")
    topic = params.get("topic") or title
    variants = yt.title_variants(title, keyword=params.get("keyword", ""))
    description = yt.build_description(
        variants[0] if variants else title,
        summary=params.get("summary", ""))
    thumbnail_brief = yt.thumbnail_brief(topic)
    metadata = {
        "title": variants[0] if variants else title,
        "title_variants": variants,
        "description": description,
        "thumbnail_brief": thumbnail_brief,
        "audience": "NOT made for kids",
        "channel": "Nova Automation",
    }
    meta_path = os.path.join(ep_dir, "metadata.json")
    _write_json(meta_path, metadata)

    # Overlay/watermark records (the finish plan; application needs ffmpeg).
    teaser_record = {
        "kind": "tiktok_teaser_watermark", "position": "bottom-right",
        "animated": True, "text": "Nova Automation",
        "icon": "youtube_play", "motion": "slide-in/out",
        "path": params.get("teaser_path") or "",
        "applied": False,
    }
    overlay_record = {
        "kind": "youtube_episode_overlay", "position": "bottom-right",
        "animated": True, "elements": ["like", "subscribe", "bell"],
        "path": params.get("episode_cut_path") or "",
        "applied": False,
    }
    _write_json(os.path.join(ep_dir, "teaser-record.json"), teaser_record)
    _write_json(os.path.join(ep_dir, "overlay-record.json"), overlay_record)

    realism_record = params.get("realism_record") or {}
    if realism_record and "items" in realism_record:
        items = realism_record["items"]
        missing = [n for n in qc.REALISM_FINAL_VALIDATION if n not in items]
        if missing:
            raise d.PipelineError(
                "realism record incomplete, missing: "
                + ", ".join(missing))
    _write_json(os.path.join(ep_dir, "realism-record.json"), realism_record)

    # Publish state: produced -> qc'd, then GATE D. The gate sees the
    # prospective "qc'd" state; we only commit it when the gate passes.
    result = qc.gate_d({
        "master_path": params.get("master_path") or "",
        "teaser": {"path": teaser_record["path"],
                   "watermark_record": teaser_record},
        "episode_cut": {"path": overlay_record["path"],
                        "overlay_record": overlay_record},
        "realism_record": realism_record,
        "metadata": metadata,
        "publish_state": "qc'd",
    })
    out_path = os.path.join(ep_dir, "gate-d.json")
    _write_json(out_path, result)
    if not result["passed"]:
        raise d.GateFailedError(
            "GATE D failed: " + "; ".join(
                f"{c['name']}: {c['detail']}" for c in result["checks"]
                if not c["passed"]))
    ctx.advance_publish_state("qc'd")
    return {
        "metadata": d.typed_value("FILE", {"url": _rel(ctx, meta_path),
                                           "mimeType": "application/json"}),
        "verdict": d.typed_value("FILE", {"url": _rel(ctx, out_path),
                                          "mimeType": "application/json"}),
        "air_slot": d.typed_value(
            "STRING", qc.next_air_slot().isoformat()),
    }


# --- node: propose_publish ------------------------------------------------------------------
def propose_publish(ctx, node, inputs):
    """Mint a post_video approvals proposal. NEVER auto-publishes; the
    pipeline never drives a browser or touches YouTube APIs."""
    from approvals import queue as approvals_queue
    metadata = inputs.get("metadata")
    if d.is_unresolved(metadata):
        raise d.PipelineError("propose_publish: metadata unresolved")
    with open(_abs(ctx, metadata["value"]["url"]), encoding="utf-8") as fh:
        meta = json.load(fh)
    params = node["params"]
    master_path = params.get("master_path") or ""
    platform = params.get("platform", "youtube")
    account = params.get("account", "Nova Automation")
    caption = f"{meta.get('title', '')}\n\n{meta.get('description', '')}".strip()
    summary = (f"[video-pipeline] publish proposal for {ctx.episode['id']} — "
               f"HUMAN APPROVAL required; airs {params.get('air_slot', '')}")
    item = approvals_queue.propose(
        ctx.home, "post_video", platform, account, summary,
        payload={"file": os.path.abspath(master_path) if master_path
                 else "", "text": caption},
        ref={"store": "video_pipeline/episodes.json", "id": ctx.episode["id"]},
        reason="pipeline GATE D passed; owner approval required before upload")
    ctx.advance_publish_state("proposed")
    return {
        "proposal_id": d.typed_value("STRING", item["id"]),
        "platform": d.typed_value("STRING", platform),
    }


# --- registry -------------------------------------------------------------------------------
EXECUTORS = {
    "parse_script": parse_script,
    "gate_a": gate_a,
    "plan_shots": plan_shots,
    "gen_shot": gen_shot,
    "qc_shot": qc_shot,
    "assemble": assemble,
    "finish": finish,
    "propose_publish": propose_publish,
}


def build_initial_nodes(script_path="", shot_plan_path="", shots=None,
                        provider="local-ffmpeg", episode_no=1):
    """The three head nodes; per-shot fan-out happens after plan_shots."""
    return [
        d.make_node("parse_script", "parse_script",
                    params={"script_path": script_path},
                    label="parse screenplay"),
        d.make_node("gate_a", "gate_a",
                    params={"episode_no": episode_no},
                    inputs={"inventory": d.input_ref("parse_script",
                                                     "inventory")},
                    deps=["parse_script"], label="GATE A pre-production"),
        d.make_node("plan_shots", "plan_shots",
                    params={"shot_plan_path": shot_plan_path,
                            "shots": shots or []},
                    deps=["gate_a"], label="plan shots"),
    ]


def expand_after_plan(shots, provider="local-ffmpeg", episode_no=1,
                      review=None, finish_params=None):
    """Materialize per-shot nodes + assemble/finish/propose_publish."""
    review = review or {}
    finish_params = finish_params or {}
    nodes = []
    qc_ids = []
    for i, shot in enumerate(shots):
        gid = f"gen_shot_{i}"
        qid = f"qc_shot_{i}"
        nodes.append(d.make_node(
            gid, "gen_shot",
            params={"shot": shot, "provider": provider,
                    "episode_no": episode_no,
                    "other": shot.get("other") or {}},
            deps=["plan_shots"], retries=3,
            label=f"generate shot {shot.get('id', i)}"))
        nodes.append(d.make_node(
            qid, "qc_shot",
            params={"review": review,
                    "expected_identity_hash":
                        shot.get("expected_identity_hash", "")},
            inputs={"clip": d.input_ref(gid, "clip"),
                    "record": d.input_ref(gid, "record")},
            deps=[gid], retries=1,
            label=f"GATE B shot {shot.get('id', i)}"))
        qc_ids.append(qid)
    clip_inputs = {f"clip_{i}": d.input_ref(qid, "accepted_clip")
                   for i, qid in enumerate(qc_ids)}
    nodes.append(d.make_node(
        "assemble", "assemble",
        params={"episode_no": episode_no,
                "lipsync_report": finish_params.get("lipsync_report") or {},
                "score": finish_params.get("score") or {},
                "srt_path": finish_params.get("srt_path") or "",
                "dialogue_windows":
                    finish_params.get("dialogue_windows") or []},
        inputs=clip_inputs, deps=qc_ids, retries=1,
        label="assemble + GATE C"))
    nodes.append(d.make_node(
        "finish", "finish",
        params=dict(finish_params),
        inputs={"assembly": d.input_ref("assemble", "assembly")},
        deps=["assemble"], retries=1, label="finish + GATE D"))
    nodes.append(d.make_node(
        "propose_publish", "propose_publish",
        params={"platform": finish_params.get("platform", "youtube"),
                "account": finish_params.get("account", "Nova Automation"),
                "master_path": finish_params.get("master_path") or "",
                "air_slot": ""},
        inputs={"metadata": d.input_ref("finish", "metadata")},
        deps=["finish"], retries=0,
        label="propose publish (human approval)"))
    return nodes
