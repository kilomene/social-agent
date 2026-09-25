"""Audio clipping/mixing via ffmpeg (stdlib subprocess; no other deps).

Same contract as video/: builders return argv (pure, testable), run_cmd()
prints the exact command before executing, outputs never overwrite inputs.
See audio/MUSIC.md for the licensing rules on source audio.
"""
