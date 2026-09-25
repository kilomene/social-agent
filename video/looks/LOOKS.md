# Signature looks — reference stills

The agent's cinematic color grades are tuned to reproduce these three reference
stills (checked 2026-09-25). Palettes below were sampled from the actual files
with PIL (120×120 downscale, pixels bucketed by luminance).

## 1. `teal-noir-night-1.jpg` — teal noir / subway night

A dark subway corridor at night. Deep teal/cyan shadows, a lone figure in a red
jacket (the only warm mass), red LED signage glowing against the cool grade.

Sampled palette:
- shadows (n=12007): rgb(17,33,43) — hue 203°, sat 0.60 — **teal-cyan**
- midtones (n=2141): rgb(29,116,133) — hue 190°, sat 0.78 — **strong teal**
- highlights (n=252): rgb(145,202,209) — hue 187°, sat 0.31 — cool cyan

Grade recipe (`teal-noir`):
- White balance pulled cold: shadows toward cyan-blue (red −, blue +), midtones
  toward teal (red −, green/blue +), highlights near-neutral, a touch warm so
  practicals (signs, lamps) pop orange against the teal.
- Blacks lightly crushed, contrast +8%, saturation +15% (midtones carry it).
- Subtle vignette.

ffmpeg (see `editor/grading.py` `teal-noir`):
`colorbalance=rs=-0.25:gs=0.10:bs=0.25:rm=-0.15:gm=0.08:bm=0.15:rh=0.05:gh=0.0:bh=-0.05,eq=contrast=1.08:brightness=-0.02:saturation=1.15,vignette=PI/5`

## 2. `neon-city-2.jpg` — neon city / Shibuya night

Rain-wet neon street, deep blue night, saturated signage (red/orange/green
neon), motion-blurred crowd.

Sampled palette:
- shadows (n=11011): rgb(11,31,51) — hue 210°, sat 0.78 — **deep blue**
- midtones (n=3268): rgb(59,110,128) — hue 196°, sat 0.54 — teal-blue
- highlights (n=121): rgb(137,201,175) — hue 156°, sat 0.32 — cool green-cyan

Grade recipe (`neon-city`): like teal-noir but deeper blue shadows, higher
overall saturation (+25%), neon highlights protected (don't clip the signs).
Slightly lifted blacks keep the wet-street reflections readable.

## 3. `teal-street-3.jpg` — teal street / dusk city

Dusk city street, wet cobblestones reflecting warm shop lights against a teal
sky and teal-washed buildings. The classic teal-and-orange split.

Sampled palette:
- shadows (n=8912): rgb(13,42,46) — hue 187°, sat 0.72 — **teal**
- midtones (n=5081): rgb(63,120,117) — hue 177°, sat 0.47 — muted teal
- highlights (n=407): rgb(182,196,180) — hue 113°, sat 0.08 — near-neutral warm

Grade recipe: teal-noir base, then warm the highlights more aggressively
(+0.10 red in highlights) so practicals bloom orange while everything else
stays teal. This is the textbook complementary-color grade.

## Using the looks

- `social-agent grade list` — all presets with their intent
- `social-agent grade apply --input in.mp4 --output out.mp4 --look teal-noir`
- `social-agent grade apply --look teal-noir --dry-run` — print the filtergraph
  without rendering
- `clean` = no grade (first-class option, per the user's "even normal effect,
  no effect")
- Brand kits (`branding/kit.yaml`) can set a default grade per account so every
  video in a batch matches.
