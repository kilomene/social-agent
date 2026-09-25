"""editor: the AI Video Editor Worker.

Pipeline: watch -> plan -> edit -> grade -> captions -> QA -> export ->
platform fit -> (approval) -> post.

Submodules:
  analyze    watch-before-edit analysis (analysis.json)
  kdenlive   Kdenlive .kdenlive (MLT XML) project authoring
  shotcut    Shotcut .mlt project authoring
  grading    cinematic grades incl. teal-noir (matches video/looks/)
  subtitles  SRT I/O, burn-in, karaoke captions, transcribe shim
  highlights auto highlight detection + clip cutting
  broll      B-roll placement planner + ffmpeg apply
  motion     lower thirds, progress bars, cards, intro/outro (PIL)
  branding   brand kit (logo/colors/fonts/grade) + consistent apply
  batch      batch ops across hundreds of files + render queue w/ resume
  qa         black/freeze/desync/corruption checks + auto re-render
  thumbnails branded thumbnails with contrast safety check
  camera     stabilization, denoise, white balance, exposure recovery
  compress   CRF ladders + 2-pass size-targeted encodes
"""
