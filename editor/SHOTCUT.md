# Shotcut — the lightweight editor

Shotcut `.mlt` files are also MLT XML but simpler than Kdenlive's: producers,
playlists, tractors, no Kdenlive-specific metadata. `editor/shotcut.py`
authors them.

## When to use Shotcut instead of Kdenlive

- Quick assembly cuts: trim, reorder, hard cuts, simple fades.
- Fast turnaround vertical videos (one track, captions, export).
- Machines where Kdenlive feels heavy.

Kdenlive wins for: multi-track productions, keyframed effects, serious color
grading (scopes + Lift/Gamma/Gain), proxy workflows, Glaxnimate round-trips.

## What the agent builds

- `Project(title, width, height, fps)` — default 1920×1080@30.
- `add_asset(path)` → producer; `add_clip(asset_id, track="v1", in_s, out_s)`.
- `save(path)` → `.mlt` + `.mlt.autosave` sidecar.
- `missing_media()` → assets not on disk (QA consumes this).
- `render_headless(output)` → renders via `melt` if installed; Shotcut itself
  has no headless CLI, so without melt you open the `.mlt` in Shotcut and use
  **Export**.

## Shotcut specifics worth knowing

- **Filters panel**: video filters (color grading, glow, vignette, chroma key,
  stabilize) and audio filters (normalize, compressor, EQ) attach per clip.
- **Keyframes** panel: keyframeable filter parameters, same linear/smooth/
  discrete interpolation ideas as Kdenlive.
- **Export**: presets for YouTube etc.; the agent's `video build_export`
  ladder (480p→8K × H.264/H.265/AV1) covers anything the GUI presets do.
- **Text**: `Text: Simple` / `Text: Rich` filters for titles and lower thirds;
  for animated captions prefer the agent's ASS karaoke path burned in with
  ffmpeg (`editor captions burn`).

## Handoff rule

Both editors' project files are plain XML the agent writes. Anything the
agent can't express in XML (complex keyframed animation, manual rotoscoping)
goes in the project markers/notes, and the doc tells the human exactly which
dock holds it.
