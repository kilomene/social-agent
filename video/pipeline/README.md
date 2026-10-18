# video/pipeline — node-based, resumable video production pipeline

Episode → scenes → shots as a **typed DAG of nodes with persistent state**,
explicit per-shot retries, QC gates (A/B/C/D), and an approvals-queue
publishing handoff. The pipeline never drives a browser, never touches
YouTube APIs, and never auto-publishes.

## Attribution

The core model (node lifecycle, typed `{dataType, value}` outputs, the
`ProviderDefinition` contract, generateMedia host flow, full-snapshot atomic
persistence, resume-by-skipping-succeeded-nodes) is a substantial derivation
of **Toonflow-app** (https://github.com/HBAI-Ltd/Toonflow-app):

> MIT License — Copyright (c) 2026 HBAI-Ltd (permission notice reproduced
> in full in `providers/__init__.py`).

What was ported vs. what is new:

| Toonflow concept | Ported as | Notes |
|---|---|---|
| Node lifecycle idle → running → succeeded/failed | `definition.py` STATUSES, `runner.py` | One node at a time: no concurrent runs per node, guaranteed |
| Typed values `{dataType, value}`; media `{url, mimeType}` | `definition.typed_value` | STRING/INT/FLOAT/BOOLEAN/IMAGE/MASK/VIDEO/AUDIO/FILE |
| Unconnected inputs | `definition.UNRESOLVED` sentinel | Explicit, distinct from null |
| `ProviderDefinition` `{id,label,version,rules[],models[]}` + generateImage/Video/Audio, getPrice, getBalance, processMedia | `providers/base.py` | Generate fns return FINAL media, never task IDs |
| Free provider = `rules: []`, hardcoded models | `providers/local_ffmpeg.py` | Only free provider; synthesizes test media via lavfi (honest, not AI) |
| generateMedia host flow (validate → resolve → read refs → call → normalize → write under lock → cleanup) | `providers/base.generate_media` | Reference files mime-sniffed, 25 MiB-capped |
| Atomic full-snapshot persistence; resume skips succeeded nodes | `state.py` | New store `<home>/video_pipeline/` (never the live loop stores) |
| Sentinel errors propagate uncaught | `definition.PipelineBlockedError/CancelledError` | Never retried, never swallowed; secrets redacted |

**Deliberate improvements over upstream** (Toonflow has no headless
executor and no node-level retries; this package is the DAG runner):
explicit per-node `retries` (per-shot retry counts), cooperative
cancellation, crash recovery (a node left `running` at shutdown re-runs),
and the social-agent QC gates below.

**Not ported:** the Vue UI, the MCP server, team/skill scaffolds.

## Workflow skills are authoritative

All video work runs under the REALISM-ENGINE Golden Law ("the viewer must
believe a real camera, real actors, and a real film crew — not AI") via the
three Workflow skills. Toonflow's approach adapts to them, never replaces
them:

- `character-consistency`: identity blocks pasted **verbatim** into every
  generation prompt (hash-verified at GATE B); locked voice IDs; self-review
  pass recorded as evidence.
- `cinematic-effect-engine`: the Core Look block prepended to every shot;
  four-layer audio (dialogue/Foley/environment/music); no in-frame
  watermarks/text; 10-item REALISM Final Validation at GATE D.
- `physics-continuity-engine`: reality-first checks folded into the
  per-shot review record; regenerate-only-the-faulty-shot discipline.

## Layout

```
video/pipeline/
  definition.py   typed values, UNRESOLVED, exceptions, node/episode specs
  state.py        atomic state in <home>/video_pipeline/ + resume helpers
  providers/      ProviderDefinition contract + importlib registry
    base.py       contract, generate_media host flow, secret redaction
    local_ffmpeg.py  FREE: lavfi test-media synthesis (not AI generation)
    stubs.py      paid/closed providers as honest PipelineBlockedError stubs
  script.py       markdown screenplay parser (scenes, dialogue inventory)
  qc.py           GATE A/B/C/D checks — never fabricate values
  nodes.py        executors: parse_script … propose_publish
  runner.py       topological DAG runner (retries, resume, cancel)
  cli.py          define / run / status / inspect / retry / mark / providers
```

## Gates

- **GATE A (pre-production):** character bible covers every speaking
  character; `voice-cast.json` (one locked voice ID per character);
  `identity-blocks/<CHAR>.md` (100–150 words, sha256-verified verbatim);
  verified master portraits; `continuity/ledger.md` read; dialogue
  inventory parsed from the markdown script.
- **GATE B (per-shot):** identity-block hash match + Core Look block in the
  generation record; REAL video only (frame-delta motion check —
  blocked/region-gated = FAIL, never pass); 16:9 edge-to-edge (black-bar
  scan); recorded self-review evidence for watermarks/artifacts/identity.
  Accept with verdicts, or reject with reason + corrective instruction.
  Failed shots regenerate ALONE.
- **GATE C (assembly):** runtime 5–10 min; every dialogue line has a TTS
  file named `voice-audio/e<NN>-s<scene>d<dialogue#>_<character>-<voiceid>.wav`
  with the locked voice ID; four-layer mix manifest per scene; audio energy
  per dialogue window; explicit `ffmpeg -map 0:v:0 -map 1:a:0` (the silent
  wrong-audio gotcha); lip-sync verdict per line; full-length original score
  ducked under dialogue; captions cover 100% of dialogue windows; no black
  frames / corrupt audio (`editor.qa.verify`).
- **GATE D (pre-publish):** master exactly 3840×2160 VP9; TikTok teaser
  bottom-right animated watermark (YouTube play icon + "Nova Automation",
  slide-in/out); YouTube episode bottom-right like/subscribe/bell overlay;
  10-item REALISM Final Validation all-pass record; metadata package (title,
  description, thumbnail brief, audience NOT made for kids, channel Nova
  Automation); air slot = next Sun/Tue/Fri 3:00 PM America/New_York; human
  approval state machine produced → QC'd → proposed → uploaded/scheduled →
  owner-approved → aired.

QC records never fabricate values: missing evidence = fail (or an explicit
null), never a guessed pass.

## Publishing

`propose_publish` mints an `approvals.queue` item of type `post_video`
with `ref={"store": "video_pipeline/episodes.json", "id": ep_id}`. It never
auto-publishes; TikTok/FB/IG `post_video` is never auto-approved. The last
three publish states (uploaded/scheduled → owner-approved → aired) happen in
the host's live browser (YouTube Studio) and are recorded with
`cli.py mark --to <state>`.

## Wired vs. stubbed (honest table)

| Capability | Status |
|---|---|
| Screenplay parsing, dialogue inventory | WIRED (`script.py`) |
| Shot planning (explicit JSON or shot-plan markdown) | WIRED (`nodes.plan_shots`) |
| Video generation (local test media) | WIRED (`local-ffmpeg` via lavfi) |
| Video generation (Muse Video / Sora / Kling / Veo) | STUBBED — `PipelineBlockedError` naming the block (region gate 403 / paid API, $0 budget) |
| TTS voice lines | STUBBED — no $0 TTS provider; GATE C fails honestly until wired |
| Concat assembly, mix manifest, explicit `-map` | WIRED (needs ffmpeg binary) |
| Motion / black-bar / black-frame / desync scans | WIRED (needs ffmpeg/ffprobe) |
| Captions build + coverage | WIRED via `editor.subtitles` (needs dialogue timing) |
| Branding overlays, 4K upscale | Recorded as finish-plan data; application needs ffmpeg + assets |
| Metadata (title/description/thumbnail brief) | WIRED via `growth.youtube` |
| Publish proposal | WIRED via `approvals.queue` (`post_video`, human approval) |
| Upload / schedule / browser work | NOT IN PIPELINE — host agent in live Chromium |

## CLI

```
python3 -m video.pipeline.cli define --episode-id e01 --title "..." \
    --project-dir <dir> --script scripts/e01.md --shots-json shots.json
python3 -m video.pipeline.cli run --episode-id e01 \
    --review-json review.json --finish-json finish.json
python3 -m video.pipeline.cli status --episode-id e01 -v
python3 -m video.pipeline.cli inspect --episode-id e01 --node qc_shot_0
python3 -m video.pipeline.cli retry --episode-id e01 --node gen_shot_0
python3 -m video.pipeline.cli mark --episode-id e01 --to uploaded/scheduled \
    --note "scheduled in YouTube Studio"
python3 -m video.pipeline.cli providers
```

Also registered on the main CLI as `bin/social-agent video-pipeline ...`.
