# Video specs — human-readable reference

Checked **2026-09-25** from the sources below. Platform rules change; re-check
before relying on these for anything load-bearing. These are summaries of
public platform guidance — the platforms' own help docs govern, not this file.

Machine-readable version: `video/specs.yaml` (used by `video fit` /
`video preflight`).

## Quick table

| Placement | Aspect | Resolution | Max duration | Max size | Container |
|---|---|---|---|---|---|
| TikTok feed | 9:16 | 1080×1920 | 10 min | 287 MB | MP4/MOV/WebM |
| YouTube long-form | 16:9 | 1920×1080 | 12 h | 256 GB | MP4/MOV/MPEG/WebM |
| YouTube Shorts | 9:16 | 1080×1920 | 3 min | 256 GB | MP4/MOV/WebM |
| Instagram Reels | 9:16 | 1080×1920 | 3 min | 4 GB | MP4/MOV |
| Instagram Stories | 9:16 | 1080×1920 | 60 s | 4 GB | MP4/MOV |
| Instagram feed | 4:5 | 1080×1350 | 60 min | 4 GB | MP4/MOV |
| Facebook feed | 4:5 | 1080×1350 | 240 min | 4 GB | MP4/MOV |
| Facebook Reels | 9:16 | 1080×1920 | 90 s | 4 GB | MP4/MOV |
| Facebook Stories | 9:16 | 1080×1920 | 60 s | 4 GB | MP4/MOV |
| X feed | 16:9 | 1920×1080 | 2:20 | 512 MB | MP4/MOV |
| Reddit feed | 16:9 | 1920×1080 | 15 min | 1 GB | MP4/MOV |

**The universal takeaway: 1080×1920, 9:16, H.264** covers every vertical slot.

## Safe zones (where the app UI eats your pixels)

- **TikTok:** right-side ~150px strip (action buttons), bottom ~250px (caption +
  progress bar), top ~150px (header). Keep text 150px clear of all edges.
- **YouTube Shorts:** bottom ~300px (title/description overlay), right side
  (action buttons).
- **Instagram/Facebook Stories:** top 14% and bottom 20% are unsafe for key
  content — profile, reply, and link UI lives there.
- **Instagram Reels:** bottom 20% caption overlay.

## Notes per placement

- **TikTok:** vertical 9:16 required. 21–34s is the highest-completion sweet
  spot even though 10 minutes is technically allowed.
- **YouTube long-form:** 16:9 landscape. Target -14 LUFS loudness.
- **YouTube Shorts:** up to 3 minutes accepted, ≤60s is the classic length.
  Put `#Shorts` in the title or description for reliable classification.
- **Instagram Reels:** up to 3 minutes accepted; 15–90s recommended.
- **Facebook feed:** 85% of watch time is silent — captions are essential.
- **X:** 16:9 landscape default, but 9:16 vertical and 1:1 square are accepted.

## Optional enhancement: face-aware cropping

`video fit --crop --focus face` works today by falling back to center when no
face model is available. If you install OpenCV (`pip install opencv-python`),
the fitter uses a Haar cascade to center the crop box on the largest detected
face in the source frame. Without it, `--focus center|top|bottom` and explicit
`--focus-x/--focus-y` fractions still work — no dependency required.

## Sources

- TikTok video specs and optimal encoding guidance (claude-skill-registry,
  2025–2026 spec tables)
- TikTok / Reels / Shorts / Reels cheat sheet (Portrait AI blog, 2026)
- Platform content specs: Instagram Reels, TikTok, YouTube Shorts
  (curatr-publishing skill, crawl 2026-09)
- Video ad specs: TikTok, Reels, Stories, YouTube, Facebook, LinkedIn
  (inference-sh skills, crawl 2026-09)
- Viral video platform specs with FFmpeg presets (claude-plugin-marketplace)
