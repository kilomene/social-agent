# Editor workflow — watch → plan → edit → grade → captions → QA → export

The autonomous editing pipeline. Every step is a CLI command; state flows
through `analysis.json` and the render queue.

```
editor watch --input raw.mp4 --out work/eps1
  │  probes duration/scenes/energy/silence → work/eps1/analysis.json
  ▼
editor highlights --dir work/eps1 --top 5        (auto highlight reels)
editor broll-plan --dir work/eps1 --broll broll/  (cutaway/pip placement)
  │  plans are JSON — inspect before applying
  ▼
editor project-new --title eps1 --profile 1080p30 --out work/eps1.kdenlive
editor project-add ... / editor project-effect ...   (timeline assembly)
  │  or: ffmpeg-only assembly via video plan / broll apply
  ▼
editor grade --input cut.mp4 --output graded.mp4 --look teal-noir
  │  grades: teal-noir, neon-city, teal-street, warm-vintage, noir,
  │  blockbuster, clean (= no effect, first-class)
  ▼
editor transcribe --input graded.mp4 --transcript words.txt --dir work/eps1
editor captions --input graded.mp4 --srt work/eps1/captions.srt --style pop
  │  whisper not installed → transcript + timing heuristic (documented);
  │  install whisper for real transcription (pip install openai-whisper,
  │  needs ffmpeg + ~1GB model download)
  ▼
editor qa --input final.mp4 --srt work/eps1/captions.srt
  │  black/freeze/desync/decode/subtitle checks; --rerender retries once
  ▼
editor export --input final.mp4 --output dist/eps1.mp4 \
    --resolution 4k --codec hevc        (480p→8k × h264/hevc/av1, hw auto)
video fit --input dist/eps1.mp4 --for tiktok     (platform sizing, pad-first)
video preflight --input dist/eps1.mp4 --for tiktok
  ▼
post draft --video dist/eps1.mp4 ... → approval → post   (approval-gated, as ever)
```

## Batch & queue

- `editor batch --op grade --look teal-noir --in "raw/*.mp4" --out dist/`
  applies one op across hundreds of files; per-file JSONL log, one failure
  never stops the batch.
- `editor queue add --name eps1-4k -- render-cmd...` then `editor queue run`
  executes; `--resume` recovers crashed runs (done jobs skipped, failed jobs
  retried within budget). `--at "02:00"` schedules via at(1) when installed,
  otherwise stores the note.

## Branding

`editor brand create --label main` writes `branding/main.yaml` (logo, colors,
fonts, default grade, caption style, intro/outro). `editor brand apply`
stamps grade + watermark consistently across a batch — every video looks like
it came from the same channel.

## Rules

- **Posting stays approval-gated.** The agent may render anything locally;
  publishing goes through `post draft → approve → done` like everything else.
- **Never overwrite inputs.** Every builder refuses output == input.
- **Every render prints its exact command** (`--dry-run` previews).
- **Grade `clean`** is always available — "no effect" is a valid creative
  choice, not a missing feature.
