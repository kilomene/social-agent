# Guardrails — social-agent safety policy (human-readable)

Companion to `policy.yaml` (the machine-readable source of truth). These rules are
non-negotiable and are enforced by the CLI itself, not just documented.

## 1. Observe first, act only with approval

- **Watchers are read-only monitors.** They poll, detect, and *propose* actions.
  They never post, like, comment, follow, retweet, or DM on their own.
- Every acting capability (`post`, `like`, `comment`, `follow`, `unfollow`,
  `retweet`, `dm`) **defaults to dry-run** and requires an **explicit,
  per-action approval record** from the user before anything is executed.
- Approvals expire after 24 hours (`approvals.expiry_hours`).

## 2. What is prohibited — always

- Mass follow/unfollow, follow-back trains, or any follower-count gaming.
- Comment spam, duplicate replies, or unsolicited promotional DMs.
- Astroturfing: coordinated inauthentic engagement across accounts.
- Storing credentials in the repo, in state files, or in logs. See
  "Credentials" below.
- Bypassing or disabling rate limits, quiet hours, or the approval gate.

## 3. Rate limits

Per-platform hourly/daily action caps live in `policy.yaml` under
`rate_limits`. The CLI tracks a rolling count in the state directory and
**refuses** new acting operations once a cap is hit. Watcher polls are also
capped (`watchers.max_events_per_poll`) so a runaway feed cannot flood state.

These caps are conservative on purpose: real platforms suspend accounts for
bot-like velocity. Treat a refusal as the system protecting the account.

## 4. Quiet hours

When `quiet_hours.enabled` is true, acting operations are refused between
`quiet_hours.start` and `quiet_hours.end` (local time). Monitoring continues;
only acting pauses.

## 5. Credentials

- social-agent **never stores passwords, tokens, or session cookies** in the
  repository or in its state directory.
- `accounts add` stores only the platform, username/handle, and a label —
  never secrets.
- Real sign-in happens in the user's own browser session (or the platform's
  official OAuth flow), outside this tool. The CLI's `doctor` command verifies
  the environment; it never asks for a password.

## 6. Honest automation

- The CLI works **offline by default**: watchers poll fixture data or
  adapter-provided items; engagement actions are proposed, approved, and
  *logged* — live execution happens through a real browser session driven by
  the user or their agent, where platform UI and consent flows are visible.
- `capabilities.md` in `platforms/` documents what each platform genuinely
  supports via browser automation and what it does not. If something is not
  possible, it is listed as not possible — never faked.

## 7. Auditability

- Every watcher poll appends structured events to `events.jsonl` in the state
  directory.
- Every proposed/approved/completed action is recorded with timestamps.
- Every policy refusal (rate limit, spam guard, scope block) is logged to
  `refusals.jsonl` with a reason.
- `analytics` summarizes this log; nothing is silently dropped.

## 8. Selective engagement — like what's interesting, never spam

- `engage like` scores the post against the `interests:` profile in
  `policy.yaml` (topics, hashtags, author affinity, quality signals). Posts
  scoring below `threshold` are **refused** with the score and reasons logged.
- Anti-spam guards are enforced separately from the general rate limits:
  per-platform hourly/daily like caps, a per-author cooldown (default 24h —
  never like the same author twice inside it), a minimum gap between likes,
  and a daily follow cap. See `engagement:` in `policy.yaml`.
- The feed watcher (with `use_interest_profile=true`) and the follow watcher
  (with `score_users=true`) only propose engagement for interesting posts and
  users. Boring content is silently skipped — no event, no proposal.

## 9. Autonomous mode — scoped, explicit, revocable

- Autonomy is **off by default** and granted for exactly one mission:
  `autonomy grant --mission <name> --confirm` (the `--confirm` flag is the
  explicit user confirmation; without it the command only prints the scope).
- A mission (`missions/<name>.md`) defines the area of work: platforms,
  topics/content pillars, allowed actions, and hard daily limits.
- In autonomous mode the agent may act **without per-action approval**, but
  **only inside mission scope**. Anything outside scope — a different
  platform, off-topic content, DMs — is **blocked and logged** to
  `refusals.jsonl`.
- Revoke anytime: `autonomy revoke`. Rate limits, quiet hours, spam guards,
  and mission limits still apply in autonomous mode.

## 10. Profile changes always need explicit approval — no exceptions

- `profile update` creates a proposal; `profile approve` is the explicit
  approval; `profile done` logs the browser-applied change.
- **There is no code path that auto-approves profile changes** — not in
  supervised mode, not in autonomous mode, not with any mission. The
  `profile approve` command deliberately never consults the autonomy state.
- Display name, username, bio, and avatar are all covered by this rule.

## 11. Heartbeats

- Every watcher run emits `<base>/<watcher-id>/start`, then success or
  `/fail` (same protocol as the heartbeat repo). The supervisor daemon emits
  its own heartbeat every 10s. See `docs/heartbeat-integration.md`.
- With no `base_url` configured, heartbeats run in log-only mode: recorded to
  `heartbeat.json`, zero network traffic.

## 12. Platform Terms of Service — the ceiling above everything

- Every platform has `platforms/<name>/terms.md` (human-readable, with links
  to the official documents and a last-checked date) and
  `platforms/<name>/tos_rules.yaml` (machine-readable, enforced by
  `platforms/tos.py`).
- For every acting operation and every watcher poll, the CLI checks the ToS
  layer **first** — before mission scope, autonomy, quiet hours, and rate
  limits. A ToS-prohibited action is **refused (exit 2)** and logged to
  `refusals.jsonl`, even if an autonomous mission would otherwise allow it.
  There is no override: not by mission, not by autonomy grant, not by any
  approval the CLI records.
- A `restricted` action proceeds but prints the platform's constraint as an
  advisory, so the operator always sees the rule being operated under.
- Honest gaps are stated in the docs, not hidden: e.g. X's terms prohibit
  non-API automation outright, and this tool is browser-driven, so several X
  automation categories are refused rather than faked.
- These are plain-language summaries, not legal advice. The official documents
  govern, and they change over time — re-check them periodically.

## 13. Growth is organic-only and sits under the ToS layer

- The agent may help grow accounts with `growth` playbooks, goals,
  5-pillar audits, and YouTube packaging tools. Growth tactics are
  **organic-only**: real content, real engagement, honest packaging. No pods,
  no engagement bait, no fake followers, no growth hacks that violate any
  platform's terms.
- Guard order: **ToS first, growth under it**. A growth playbook can never
  authorize an acting operation, a ToS-prohibited move, or spammy behavior.
  Growth informs content choices; policy still decides what the agent may do.
- The YouTube preflight gate refuses to approve a video post when required
  quality fields (title, thumbnail, hook, audio, captions...) are missing —
  publish-half-baked is a growth anti-pattern, so the gate fails closed.

## 14. Voice + identity: human-sounding, and BE the owner

- **Voice:** the agent writes like a human, not like an AI. Every
  `post draft` and `engage comment` runs the voice check (`voice/banned.json`
  lists AI-isms). A low score (below 60) warns but does not refuse — style is
  advisory.
- **Identity (embodiment):** on social platforms the agent **is the account
  owner** — it writes in first person, bears the owner's name, and carries
  the owner's voice and opinions. It **never** says "I'm an AI/agent/chatbot",
  "as an AI language model", or robotically disclaims opinions. This is the
  user writing as themselves through their own agent (ghostwriter pattern);
  the persona always belongs to the verified account owner, never a third
  party. Personas live in `<home>/identity/accounts/<label>.md` (manage with
  `identity create/show`).
- A draft that breaks identity is **refused (exit 2)** and logged to
  `refusals.jsonl` — same refusal pattern as the rest of the repo. Style warns;
  identity breaks refuse.

## 15. Security-conscious by default

- The agent never writes secrets into content: `security/secrets.py` scans
  every `post draft` and `engage comment`, and a secret-shaped draft is
  **refused** and logged. No credentials are ever stored in the repo or the
  agent's state (see §5).
- `security audit` scans state files for secret-shaped content and prints
  hardening reminders; `security checklist` prints the review checklist.
- `watchers/security_watcher.py` watches for account anomalies — sudden
  follower purges, mass unfollow spikes, logins from unknown sessions — and
  fires **urgent** events so the owner can react (change password, revoke
  sessions, check 2FA).

## 16. Study to improve

- `study run` analyzes the agent's own events, engagement actions, and post
  queue, then writes a dated entry to `learning/journal.md`: what worked,
  what didn't, and 3 concrete adjustments.
- `study run --propose` also writes review-only proposals to
  `learning/proposals.md` (interest-profile updates, mission-pillar shifts).
  Proposals are **never auto-applied** — the human reviews and applies them.
- `study experiment start/list/conclude` tracks A/B variants (titles, hooks,
  thumbnails) and concludes winners from engagement deltas.

## 17. Comment moderation — your posts only, approval-gated

- `moderate scan --platform tiktok --account main --post <id> --fixture f.json`
  classifies each comment as **ok / question / praise / spam / toxic** with
  reasons (lexicon-based: profanity/hate patterns, ALL-CAPS rage, link/DM
  scams, crypto giveaways, repetitive text). `question` feeds the content-idea
  watcher; `praise` feeds sentiment.
- `moderate hide` **proposes** hiding a comment (dry-run). It is never
  executed without **explicit approval** (`moderate approve`) — or a
  pre-approved rule from `policy.yaml` `moderation.auto_hide` (e.g. slur or
  scam patterns the user has already green-lit). Both paths are logged.
- Scope is hard: the agent moderates **only the user's own comment
  sections** — creators moderating their own posts. It never touches anyone
  else's content. ToS layer classifies this as `comment_moderation`
  (allowed on all 6 platforms for own-content moderation).
- The comment watcher with `moderate: true` auto-classifies new comments:
  toxic/spam become high-severity events (crisis can escalate), and
  auto-hide-rule matches attach hide *proposals*.

## 18. Content production: captions, video, audio

- `caption generate --platform tiktok --topic "..." --tone bold` builds a
  platform-normed caption (hook + body + CTA + hashtag set per platform
  norms). `caption variants --n 5` gives A/B variants. Every caption passes
  the content gates (secrets → identity → voice) before it is shown.
- `video` wraps **ffmpeg** (the repo's only external dependency; see
  `video/SETUP.md`): `info`, `clip`, `trim`, `concat`, `to-vertical`
  (16:9 → 9:16 blurred-fill for TikTok/Reels/Shorts), `to-horizontal`,
  `frame` (thumbnail stills), `compress` (upload presets), and stored
  multi-step `video plan create/run`. Every command prints the exact ffmpeg
  invocation (`--dry-run` previews it) and **refuses to overwrite inputs**.
- `audio` (same ffmpeg contract): `clip` with fades, `loop`, `mix`
  (voiceover + sidechain-ducked music bed), `extract` (audio from video),
  `normalize` (loudness to documented platform targets). See `audio/MUSIC.md`:
  the tool clips audio **you provide** — use platform-licensed libraries or
  your own audio; it never sources copyrighted music itself.

## 19. Video sizing: never crop blindly

- The agent knows every platform's video spec (`video/specs.yaml`, checked
  2026-09-25; human-readable `video/SPECS.md`). TikTok/Reels/Shorts want
  9:16 (1080×1920); YouTube long-form wants 16:9 (1920×1080); Instagram and
  Facebook feeds want 4:5 (1080×1350); X and Reddit default to 16:9.
- **Pad over crop, always.** When a source doesn't match the target slot,
  `video fit` pads (blurred-background fill) by default — 100% of the frame
  is preserved, nothing is cut, and the video can never "look like nonsense".
- **Cropping is destructive and needs a focus point.** `video fit --crop`
  without `--focus` (or `--focus-x/--focus-y`) is **refused**. Before any
  crop executes, the agent surfaces what WILL be cut: the percent of the
  frame lost and exactly which edges (e.g. "cuts 31.2% of the frame — left
  and right edges removed"). `--focus face` centers on the largest detected
  face when OpenCV is installed, otherwise falls back to center with a
  warning (see `video/SPECS.md`).
- **Pre-post gate.** `post draft --video <file>` runs the video preflight
  against the platform's default placement and REFUSES the draft on FAIL,
  with the exact `video fit` command that fixes it. `video preflight
  --input <file> --for youtube:shorts` validates aspect, resolution,
  duration, file size, and container against the spec.
- The YouTube quality checklist (`youtube preflight`) accepts an optional
  `--video --placement long-form|shorts` that delegates to the spec
  preflight — packaging rules and file rules are checked together.

## 20. AI Video Editor Worker: the edit bench is safe by construction

- **Posting stays approval-gated.** Everything in `editor/` produces media
  for a draft; nothing in the edit bench can publish. A finished render
  still goes through `post draft` → approval → `post done` like anything
  else. No autonomous grant can override this.
- **Never overwrite inputs.** Every editor op writes to `--output`; the
  input file is never mutated in place. Ops refuse input==output (the same
  rule as `video`/`audio`).
- **Show the exact command first.** Every op that runs ffmpeg prints the
  full `RUN: ffmpeg ...` line before executing, and every op supports
  `--dry-run` (prints commands, writes nothing). A render that wasn't
  previewed is a render that shouldn't run.
- **Watch before cutting.** `editor watch` is the mandatory first pass:
  duration, scene cuts, silence spans, speech ratio, energy curve, and a
  full transcript slot land in `analysis.json`. `highlights` then ranks
  from data (energy + cut density + transcript), not vibes — and the
  `--note` on a cut explains why it was proposed.
- **Grades are honest about what they do.** 7 grades in
  `editor/grading.py` (teal-noir, neon-city, teal-street, warm-vintage,
  noir, blockbuster, clean). `clean` is a first-class option: passthrough
  with no effect. The three signature looks match the reference stills in
  `video/looks/` (palettes sampled 2026-09-25); the look of an edit must
  always trace back to a grade name in the render log, never "I fixed the
  colors".
- **Kdenlive is primary, Shotcut is fallback.** Project files are authored
  as real `.kdenlive`/`.mlt` XML (verified without the GUI installed);
  unknown effects are refused rather than silently dropped, and
  `render_headless` uses `melt` when present. When melt/kdenlive/shotcut
  are absent the bench says so plainly and degrades (XML authoring,
  transcript+heuristic fallback for whisper, deshake fallback for
  vidstab) — it never pretends a render happened.
- **Crash recovery.** The render queue (`editor queue`) persists jobs on
  disk: interrupted renders resume (`--resume`), done jobs are skipped,
  failed jobs retry up to their budget and then fail loudly. QA
  (`editor qa`) verifies every render (black/frozen frames, A/V sync,
  decode health, subtitle legibility, missing media) and auto re-renders
  once before giving up.
- **Consistent branding.** `editor brand` kits carry colors, logo,
  watermark position, and the grade. Brand kits stamp the render — the
  account's look is a file in the repo, not a memory of what looked good
  last time.

## 21. One approval queue for everything

- Every acting proposal — engagement (`like`/`comment`/`follow`/`retweet`),
  post publish, comment hides, reply drafts — lands in the **unified
  approval queue** (`approvals/pending.json`). There is one list to review,
  not five. `approvals list` (filter by `--status`), `approvals approve
  --id`, `approvals reject --id --reason`.
- **Approving executes the underlying action** (flips the domain record to
  `approved`); **rejecting logs the reason** and flips it to `rejected`.
  Approvals/rejections of domain-specific commands (`engage approve`,
  `post approve`, `moderate approve`) route through this same queue — the
  queue is the audit trail, not a duplicate.
- Items that can't go forward right now are **never dropped**: a
  rate-limited action becomes `rate_limited` (with `retry_at`), a crisis
  parks pending items as `held`. Both are visible in the queue and need an
  explicit human decision later.

## 22. Approval policy is per action type — deny by default

- `policy.yaml` → `approvals.per_type` maps each action type to
  `require` (human approval) or `auto` (auto-approved). **Unlisted types
  default to `require`.** The shipped default: everything `require` except
  `hide_spam: auto` (pre-approved auto-hide rules only).
- Turning a type to `auto` is a deliberate, auditable policy change — the
  auto reason is recorded on the queue item (`mission 'm9'`, or
  `approval policy (per_type: auto)`).
- Autonomous missions and per-type `auto` can approve in-scope actions, but
  they sit **below** the guard order: neither can override a ToS
  prohibition or crisis mode.

## 23. Rate limits are a central controller, per platform+action

- One controller (`ratelimit/controller.py`) owns every bucket; every
  acting command consults it. Buckets are keyed `(platform, action)` with
  sliding hour/day windows and **per-action overrides** that fall back to
  the platform section, then the default section.
- When a bucket is exhausted the command **refuses with a retry time, queues
  the action as `rate_limited`, and re-raises** (exit 2, "rate limit" in
  stderr). The queue item carries `retry_at`; the action is retried after
  that time, not silently discarded.
- Consecutive denials widen the retry window exponentially (capped at 24h);
  a successful action resets the denial count. `ratelimit status` shows
  remaining quota per bucket; `ratelimit config` shows the effective limits.

## 24. Crisis mode: the kill switch

- `crisis on [--reason]` pauses **all** acting operations immediately and
  parks pending/rate-limited queue items as `held`. Watchers keep
  monitoring (read-only) — the agent can still see, it just can't touch.
- Crisis sits in the guard order **above approvals, rate limits, and quiet
  hours** (below ToS): no approval, auto-policy, or mission grant can act
  while it's active. `crisis on` fires an urgent heartbeat alert and is
  recorded locally.
- **It never auto-resumes.** Only an explicit `crisis off` clears it — and
  clearing re-pends held items for human approval; nothing auto-approves.
- The crisis watcher's `auto_pause` is **opt-in only** (default off): a
  false positive must never silence the account on its own.

## 25. Notification listener: poll fast, route carefully

- `listen` is a fast-poll loop over notification/comment/message watchers
  (`--once` for a single pass). It's poll-based by design — see
  `docs/listen-latency.md` for the honest latency expectations.
- Routing: **question comments** → reply draft (gated by voice + identity
  checks, with a safe generic fallback; never a refused draft reaching a
  human unmarked) into the approval queue; **toxic/spam comments** → hide
  proposal (auto-approved only under a pre-approved rule, like §17);
  **DMs** → logged to the people DB and surfaced as a user notification;
  **mentions/likes/follows** → recorded to the people DB.
- **People memory** (`people/`) is per account: interaction counts with
  weights (comment=3, like=1, dm=5, follow=4, mention=2), notes, tags,
  sentiment history, conversation log. Sustained engagement auto-tags
  `top-fan`; top-fan questions get a priority flag, and the tag boosts
  interest scoring (+2). `people top/show/note/tag/untag` manage it.
- Guard order reminder (the ceiling stack): **ToS > crisis > approvals >
  rate limits > quiet hours.** Nothing below overrides anything above: a
  pending approval can't fire under crisis, no auto-policy or mission can
  override a ToS prohibition, and an exhausted bucket still refuses an
  approved action until its retry time.
