# YouTube growth guide (for the social-agent)

Organic YouTube growth is **packaging + retention + consistency**. The
algorithm promotes videos that earn clicks and keep people watching. Nothing
here is fake engagement — botting views/subs is prohibited by YouTube's terms
(see `platforms/youtube/terms.md`) and by this repo's guardrails.

## 1. Packaging decides 80% of performance

- **Title**: one promise, one keyword near the front, ≤60 chars so it doesn't
  truncate. Use `youtube titles "raw idea"` to generate 5 scored variants.
- **Thumbnail**: custom, high-contrast, ≤3 words, expressive. Never an
  auto-frame. Use `youtube thumbnail-brief` for a design spec.
- Title and thumbnail must make **one combined promise** — never contradict.

## 2. The first 30 seconds

- Open by paying off the title immediately, then tease what's coming.
- No animated intros, no "hey guys welcome back", no throat-clearing.
- `youtube preflight` blocks approval until the 30-second hook is confirmed.

## 3. Retention editing

- Cut every dead second. New visual every 3–8 seconds (b-roll, zoom, graphic).
- Open loops: promise a payoff later ("at the end I'll show the exact prompt").
- Chapters/timestamps for videos over ~8 minutes.

## 4. Cadence

- 1–2 long-form videos/week + 3–5 Shorts/week while growing.
- Shorts are discovery; long-form builds subscribers and watch time.
- Consistency for 90 days before judging a format.

## 5. Descriptions (SEO + conversion)

- First 2 lines: keyword-rich summary (this is what search shows).
- Then timestamps, links, CTA, hashtags. Use `youtube description`.
- Pinned comment with a question to seed discussion.

## 6. What to measure weekly

- CTR (aim 4%+; below 2% = packaging problem),
- Average view duration / retention curve (find the drop-off, fix it next video),
- Subscribers per video, returning viewers.
- Feed these into `study run` — the learning loop proposes pillar shifts.

## 7. Hard rules

- Never buy views/subs, never use view-botting services — account-killing.
- Never mislead with title/thumbnail the video doesn't deliver (retention dies).
- The CLI drafts and gates; publishing happens in a real session by the human.
