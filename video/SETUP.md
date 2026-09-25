# video/SETUP.md — ffmpeg setup for social-agent video editing

`social-agent video` and `social-agent audio` shell out to **ffmpeg**
(and ffprobe for `video info`). They are the only external dependency in
the whole repo — everything else is pure stdlib Python.

## This environment

ffmpeg **is installed** here (`/usr/bin/ffmpeg`, version 8.1.2, checked
2026-09-25), so all video/audio commands run for real. `social-agent
doctor` reports ffmpeg status.

## Installing elsewhere

- **Ubuntu/Debian:** `sudo apt install ffmpeg`
- **macOS:** `brew install ffmpeg`
- **Windows:** download a static build from https://www.ffmpeg.org/download.html
  and add it to PATH.

Verify with: `ffmpeg -version` and `ffprobe -version`.

## Without ffmpeg

Every `video`/`audio` command refuses gracefully with a message pointing
here (nothing half-runs). The command *builders* (`video/ffmpeg.py`,
`audio/clips.py`) are pure functions — tests exercise them without ffmpeg.

## Notes

- Outputs never overwrite inputs (refused by every builder).
- Every command prints the exact ffmpeg invocation before running it
  (transparency: you can copy-paste it yourself).
- Edit plans (`video plan create/run`) chain builders with temp
  intermediates; dry-run mode prints commands without executing.

## Optional: face-aware cropping

`video fit --crop --focus face` centers the crop box on the largest detected
face. It needs OpenCV:

```bash
pip install opencv-python
```

Without it, `--focus face` falls back to center with a warning — and
`--focus center|top|bottom|left|right` or explicit `--focus-x/--focus-y`
fractions work with no dependency at all.
