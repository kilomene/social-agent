---
name: "social-agent"
description: "Autonomous social-media monitoring toolkit: 14 poll-based watchers (notifications, comments, feed, follows, activity, channels, messages, trends, competitors, sentiment, mentions, velocity, content-ideas, crisis) plus approval-gated posting, selective engagement (like/follow only what's interesting, spam-guarded), scoped autonomous missions, and protocol-compatible heartbeats across TikTok, X, Instagram, Facebook, YouTube, Reddit. Watchers observe and propose; acting requires explicit per-action approval or a scoped autonomy grant. Pure stdlib, works offline."
---

# social-agent skill

Install and use the social-agent toolkit from the `social-agent` repo.

## Install

```bash
git clone <repo-url> ~/workspace/social-agent
cd ~/workspace/social-agent && ./install.sh   # creates ~/SocialAgent/ (its own brain)
export PATH="$HOME/workspace/social-agent/bin:$PATH"
export SOCIAL_AGENT_HOME="$HOME/SocialAgent"   # isolated install dir
social-agent doctor
```

Requirements: Python 3.8+, nothing else (pure stdlib).
`install.sh` is idempotent; `--home <dir>` makes another isolated install.

## Permanent memory, backups, crash recovery

- Memory: `social-agent memory query|remember|recall|relate|graph|sop|campaign|schedule|content|voice|account`
  — SQLite at `<home>/memory.db`; `query` is SELECT-only.
- Backups: `social-agent backup list|snapshot|diff|restore` — content-addressed
  snapshots fire automatically on post drafts, renders, account changes,
  memory writes, and before risky actions. `restore` dry-runs by default
  and only ever *stages* (never overwrites live files).
- Crash recovery: `social-agent recover [--execute]` — replays the action
  journal, verifies each unfinished intent against real state, skips the
  already-done (no duplicate posts), never auto-executes platform actions.
- Guardrails §26 (policy/guardrails.md); scale-up notes in core/POSTGRES.md.

## Persistent browser automation (no APIs)

- Engine: Playwright/Chromium (`pip install playwright && playwright install chromium`;
  see `browser/SETUP.md`). Tests use a simulated driver — never a real browser.
- `social-agent browser login --account <label> --platform <p>` — headed
  first login (the human signs in; agent never sees the password).
  Profiles persist at `<home>/accounts/<label>/browser-profile/`.
- `social-agent browser act --account <l> --platform <p> --action like
  --target <url> [--simulate]` — one browser-backed action (like, comment,
  follow, post_text/video, dm_send, hide_comment...). Every action is
  ToS-checked first, human-paced, rate-limited, and journaled.
- 2FA/challenge → pause + user notification, never bypass.
- Recipes: `platforms/browser/` (selectors rot — re-check discipline).
  Ops doc: `docs/browser-ops.md`.
- ToS: X browser engagement is `prohibited`/fail-closed by default;
  `tos.acknowledged_risk: [x]` downgrades to restricted ONLY with a loud
  logged advisory (guardrails §27, `platforms/x/terms.md`).

## Safety model (read policy/guardrails.md first)

- Watchers are **read-only**: they poll, detect, and *propose* — never act alone.
- `post` / `engage` create **dry-run proposals**; each needs an explicit
  `approve` before anything may be performed, and performance happens in a real
  browser session, logged with `engage done`.
- **One approval queue** (`approvals list/approve/reject`): every proposal —
  engagement, publish, hides, reply drafts — is reviewed in one place with a
  per-type require/auto policy (default: require). Approving executes the
  underlying action; rejecting logs the reason.
- **Selective engagement**: likes/follows only for posts/users scoring as
  interesting against the `interests:` profile; anti-spam guards (like caps,
  per-author cooldown, min gap, follow caps) refuse spam patterns with reasons.
- **Rate limits** are enforced per (platform, action) by a central
  controller; an exhausted bucket refuses with exit 2 and queues the action
  as `rate_limited` with a retry time — never dropped.
- **Crisis mode** (`crisis on/off`) is the global kill switch: it pauses all
  acting, parks pending items as held, and never auto-resumes. Watchers keep
  monitoring read-only.
- **Autonomous mode** is off by default; grant per-mission with
  `autonomy grant --mission <name> --confirm`. In-scope actions auto-approve;
  out-of-scope actions are blocked and logged.
- **Profile changes always need explicit `profile approve`** — no exceptions,
  even in autonomous mode.
- **Notification listener** (`listen once`): questions → reply draft queued
  for approval; toxic/spam → hide proposal; DMs → people memory + user
  notification. People memory (`people top/show/note/tag`) tracks recurring
  followers; sustained engagement auto-tags top fans.
- Guard order (nothing below overrides anything above):
  **ToS > crisis > approvals > rate limits > quiet hours.** Per-platform
  quiet hours are enforced by the CLI and refuse with exit code 2.
- Never store credentials in the repo or state. Sign in happens in the user's
  own browser.

## Quickstart

```bash
# 1. Register an account (handle only — no secrets)
social-agent accounts add --platform tiktok --username somehandle --label main

# 2. Start watchers (fixtures let everything run offline)
social-agent watch start --type notification --platform tiktok --account main \
  --fixture watchers/fixtures/notifications.json
social-agent watch start --type trend --platform tiktok --account main \
  --set use_interest_profile=true --fixture watchers/fixtures/trend.json
social-agent watch start --type crisis --platform tiktok --account main \
  --fixture watchers/fixtures/crisis.json

# 3. Poll (each run emits a heartbeat: <watcher-id>/start -> ok|/fail)
social-agent watch run <watcher-id>
social-agent watch events --limit 10

# 4. Selective engagement: scored like proposal, then approve + log
social-agent engage like --platform tiktok --account main --target vid123 \
  --author creator_x --text "sora ai video tutorial" --likes-count 500
social-agent engage approve <action-id>
# ... perform the like in a real browser session ...
social-agent engage done <action-id> --result "liked in browser session"

# 5. Draft and approve posts
social-agent post draft --platform tiktok --account main --text "Hello world"
social-agent post approve <post-id>

# 6. Autonomous mission (scoped, revocable)
social-agent mission create --name growth --platforms tiktok \
  --topics "ai video" --actions post,like --limit posts_per_day=2
social-agent autonomy grant --mission growth --confirm
social-agent autonomy revoke

# 7. Profile changes (explicit approval always)
social-agent profile update --account main --bio "AI video daily"
social-agent profile approve <proposal-id>

# 8. Heartbeats + research + analytics
social-agent heartbeat status
social-agent research "AI video" --platforms tiktok,x
social-agent analytics --days 7

# 9. Growth, voice, identity, study (organic-only, under the ToS layer)
social-agent growth playbook --platform youtube
social-agent growth goals set --platform youtube --account main \
    --target-followers 10000 --deadline 2026-12-31
social-agent growth audit --platform youtube --account main --followers 850 \
    --posts-per-week 3 --niche "AI video tutorials" --has-bio --has-avatar
social-agent youtube titles "my sora workflow" --keyword sora
social-agent youtube preflight --title "..." --thumbnail thumb.png \
    --hook-30s --audio --retention-edit --captions --end-screen
social-agent voice check --text "draft..." --platform tiktok

# 10. Operations: approvals, people, rate limits, crisis, listener
social-agent engage like --platform tiktok --account main --target v1
social-agent approvals list && social-agent approvals approve --id <q-id>
social-agent people top --account main
social-agent ratelimit status
social-agent crisis on --reason "..."   # kill switch; crisis off to resume
social-agent listen once                # route comments/DMs/notifications
# Guard order: ToS > crisis > approvals > rate limits > quiet hours.
social-agent identity create --account main --name "Owner Name" \
    --voice-traits "dry humor, short sentences"
social-agent identity check --text "draft..." --account main
social-agent security audit
social-agent study run --propose
```

Every `post draft` and `engage comment` automatically runs content gates:
secret-shaped text is **refused**, identity breaks (claiming to be an AI) are
**refused**, AI-ish voice **warns** — see `policy/guardrails.md` §14–15. The
agent writes **as the account owner** (ghostwriter pattern; persona always
belongs to the verified account owner, never a third party). Growth is
organic-only and sits under the ToS layer (§13).

## Watcher types (15)

`notification` `comment` (add `moderate: true` to auto-classify new comments:
toxic/spam → high-severity events, auto-hide-rule matches → hide proposals)
`feed` `follow` `activity` `channel` `message`
`trend` (trending topics filtered by interests) `competitor` (rival cadence +
deltas digest) `sentiment` (sentiment-shift alerts) `mention` (unified
@mentions) `velocity` (viral-velocity early alerts) `content-idea` (repeated
audience questions → video ideas) `crisis` (negative-spike urgent alerts)
`security` (follower purges, mass unfollows, unknown sessions — urgent alerts)
— see `watchers/` for each config schema.

## Moderation + content production

- `moderate scan/hide/approve/done/list` — comment moderation on **your own**
  posts only: lexicon classifiers (ok/question/praise/spam/toxic),
  approval-gated hides, pre-approved `moderation.auto_hide` rules in
  policy.yaml. Guardrails §17.
- `caption generate/variants` — platform-optimized captions (hook + body +
  CTA + hashtag norms), run through the voice + identity gates. Guardrails §18.
- `video info/clip/trim/concat/to-vertical/to-horizontal/frame/compress/plan`
  — local editing via **ffmpeg** (the only external dependency; see
  `video/SETUP.md`). Prints exact commands (`--dry-run`), never overwrites
  inputs.
- `video fit/preflight` — smart aspect-ratio fitting against `video/specs.yaml`
  (checked 2026-09-25; `video/SPECS.md`). `--for tiktok[:feed]`,
  `youtube:shorts|long-form`, etc. Default strategy is **pad** (blurred fill,
  nothing cut); `--crop` needs `--focus center|top|bottom|left|right|face`
  (face needs OpenCV, else falls back to center with a warning) and surfaces
  what will be cut before executing. `video preflight` validates aspect,
  resolution, duration, size, container against the spec with concrete fixes.
  `post draft --video <file>` runs the gate and refuses the draft on FAIL.
  Guardrails §19.
- `audio clip/loop/mix/extract/normalize` — same ffmpeg contract; mixes duck
  the music bed under voiceover via sidechain compression; loudness presets
  per platform. Music must come from licensed libraries or your own audio
  (`audio/MUSIC.md`). Guardrails §18.
- `editor` — the AI Video Editor Worker (see `editor/WORKFLOW.md`): `watch`
  (mandatory first pass: scenes, silence, speech, energy, transcript) →
  `highlights` (data-ranked selects, sliding windows + non-max suppression)
  → `grade` (7 cinematic grades incl. teal-noir/neon-city/teal-street matched
  to the reference stills in `video/looks/`; `clean` = no effect) →
  `transcribe` (whisper or transcript+heuristic) → `captions` (burn-in styles,
  karaoke ASS) → `broll-plan`/`broll-apply` (PiP/cutaway over dead air) →
  `project` (real Kdenlive `.kdenlive` / Shotcut `.mlt` XML for GUI polish;
  docs in `editor/KDENLIVE.md`, `editor/SHOTCUT.md`) → `motion` (lower thirds,
  text cards, intro/outro, emoji captions) → `brand` (kits: colors, logo,
  watermark, grade) → `batch` (multi-file ops) → `queue` (persistent render
  queue with `--resume` crash recovery) → `qa` (black/freeze/desync/decode/
  subtitle checks + one auto re-render) → `thumb` (contrast-checked branded
  thumbnails) → `export` (480p→8K, h264/hevc/av1, hw encoders auto-detected)
  → `camera` (stabilize/denoise/white-balance) → `compress` (CRF ladders +
  2-pass). Every op prints its exact ffmpeg command (`--dry-run` anywhere),
  never overwrites inputs, and posting stays approval-gated. Guardrails §20.

## Environment overrides (for tests)

- `SOCIAL_AGENT_HOME` — state directory.
- `SOCIAL_AGENT_POLICY` — alternate policy.yaml (e.g. to test quiet hours).
- `SOCIAL_AGENT_HEARTBEAT` — alternate heartbeat.yaml.
- `SOCIAL_AGENT_MISSIONS` — alternate missions directory.

## What it cannot do

See `platforms/capabilities.md` for the honest per-platform matrix. The CLI
never posts/likes/comments by itself; live execution is always a real browser
session with the user's own sign-in. Docs: `docs/heartbeat-integration.md`.
