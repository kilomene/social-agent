# Kdenlive — the agent's primary GUI editor

Kdenlive is the primary editor for full productions. FFmpeg handles
pre/post-processing; Kdenlive handles the timeline, effects stack, keyframes,
and final render. Shotcut (`editor/SHOTCUT.md`) is the lightweight alternative
for quick assembly cuts.

## Project model (what `editor/kdenlive.py` builds)

Kdenlive `.kdenlive` files are **MLT XML**. The agent authors them directly:

- **Project Bin** (`main_bin` playlist) — every imported asset becomes a
  `<producer>` with a `resource` path. `project.add_asset(path)` registers
  MP4/MOV/MKV/AVI/GIF/PNG/JPG/SVG/MP3/WAV/FLAC + fonts.
- **Timeline** (`tractor` + one `playlist` per track) — `project.add_clip(
  asset_id, track="v1", in_s=0, out_s=12)` places clips. Tracks: `v1`, `v2`…
  (video), `a1`, `a2`… (audio). The agent refuses to put audio on a video
  track and vice versa.
- **Effects** — `project.add_effect(clip_id, "lift-gamma-gain", params)`.
  Named effects map to real Kdenlive effect ids and MLT services:

| name | Kdenlive effect | use |
|---|---|---|
| `lift-gamma-gain` | Lift Gamma Gain | cinematic primary grade (shadows/mids/highs) |
| `color-balance` | Color Balance | white-balance fixes |
| `color-grading` | Color Adjustment (frei0r) | per-channel brightness/contrast |
| `vignette` | Vignette | cinematic edge falloff |
| `blur` | Blur | keyframeable, for focus pulls / censor |
| `glow` | Glow | neon bloom on night footage |
| `chroma-key` | Chroma key | green-screen removal |
| `transform` | Transform | position/scale/rotation, fully keyframeable |
| `fade-in` / `fade-out` | Brightness (animated) | dips to/from black |

- **Markers** — `project.add_marker(time_s, comment)` for edit notes, sponsor
  slots, b-roll cues.
- **Autosave** — every `save()` writes a `.kdenlive.autosave` sidecar; Kdenlive
  itself also keeps timed backups (`~/.local/share/kdenlive/`).

## Keyframes (the animation system)

Every effect parameter can change over time. In the GUI: click the
stopwatch/diamond icon next to a parameter, set values at playhead positions.
Right-click a keyframe to choose interpolation:

- **Linear** — constant rate of change. Fades, simple moves.
- **Smooth (Bezier)** — eases in/out. Natural-feeling position animation.
- **Discrete** — instant jump at the keyframe. Visibility toggles, strobes.

Rule: two keyframes define a transition. Add more only when the motion needs it.

## Color workflow (matches `video/looks/`)

1. **Correct** first: white balance (`color-balance`), exposure
   (`lift-gamma-gain` lift/gain).
2. **Grade**: `lift-gamma-gain` for the teal-noir look — lift toward teal,
   gain slightly warm; or apply a LUT effect with an exported `.cube`.
   Scopes dock: **histogram, waveform, vectorscope, RGB parade** — watch the
   vectorscope while pushing teal; skin tones should stay near the skin-tone
   line.
3. **Finish**: `vignette`, subtle `glow` on neon practicals.

The agent's ffmpeg grades (`editor/grading.py`) are the render-farm equivalent
of this stack — same look, no GUI needed.

## Render profiles (Project > Render)

Built-ins include MP4-H264/AAC (web), and the agent's export ladder
(`video build_export`) covers **480p / 720p / 1080p / 1440p / 4K / 8K** in
**H.264 / H.265 / AV1**, MP4/MOV/MKV/WebM, with hardware encoding
(NVENC/QSV/VAAPI) auto-detected. For 8K: use H.265 or AV1, proxy editing on,
and render overnight via the render queue (`editor queue`).

## Proxy editing & performance

Settings > Configure Kdenlive > Timeline: enable **proxy clips** for 4K/8K —
edit on lightweight proxies, render at full resolution. Timeline preview
render (`Project > Render timeline preview`) for heavy effect stacks.

## Rotoscoping / masking note

Kdenlive has no true rotoscoping. For animated masks use the **Rotoscoping**
effect (basic) or round-trip through **Glaxnimate** (integrated: clip >
Edit with Glaxnimate) for vector shape animation, then composite back.

## Headless rendering

If `melt` is installed (`sudo apt install melt`), `project.render_headless(
output)` renders the `.kdenlive` without opening the GUI. Otherwise: open the
file in Kdenlive and render from Project > Render.
