# social-agent

An autonomous social-media monitoring toolkit for AI agents. Poll-based
watchers observe TikTok, X, Instagram, Facebook, YouTube, and Reddit and
**propose** actions; acting (post, like, comment, follow, retweet, DM) is
dry-run by default and requires explicit per-action approval. Pure Python
stdlib — no dependencies, no binaries, no credentials stored.

## Install

```bash
git clone https://github.com/kilomene/social-agent.git ~/workspace/social-agent
export PATH="$HOME/workspace/social-agent/bin:$PATH"
social-agent doctor
```

Requirements: Python 3.8+. State lives in `~/.social-agent`
(override with `SOCIAL_AGENT_HOME`).

## Quickstart

```bash
# register an account (handle only — never a password)
social-agent accounts add --platform tiktok --username somehandle --label main

# start watchers (fixtures make everything work offline)
social-agent watch start --type notification --platform tiktok --account main \
    --fixture watchers/fixtures/notifications.json
social-agent watch start --type trend --platform tiktok --account main \
    --set use_interest_profile=true --fixture watchers/fixtures/trend.json

# poll + review
social-agent watch run <id>
social-agent watch events --limit 10

# selective engagement: likes only for interesting posts, spam-guarded
social-agent engage like --platform tiktok --account main --target vid123 \
    --author creator_x --text "sora ai video tutorial" --likes-count 500

# drafts need approval too
social-agent post draft --platform tiktok --account main --text "Hello"
social-agent post approve <post-id>

# research plans + analytics
social-agent research "AI video" --platforms tiktok,x
social-agent analytics --days 7
```

## Autonomous mode (missions)

Define an area of work, then grant autonomy explicitly:

```bash
social-agent mission create --name ai-video-growth \
    --platforms tiktok,instagram --topics "ai video,sora,veo" \
    --actions post,like,follow,comment --limit posts_per_day=2
social-agent autonomy grant --mission ai-video-growth --confirm
# ... agent acts inside mission scope without per-action approval ...
social-agent autonomy revoke
```

In autonomous mode the agent may post/like/follow/comment **without
per-action approval, but only inside the mission scope** (platforms, topics,
allowed actions). Off-scope actions — other platforms, off-topic content,
DMs — are blocked and logged to `refusals.jsonl`. Profile changes **always**
need explicit `profile approve`, even in autonomous mode. See
`policy/guardrails.md` §9–10.

## Growth, voice, identity, study

Organic growth tooling — all under the ToS layer (§13), all defensive:

```bash
# organic playbooks + goals + account audits
social-agent growth playbook --platform youtube
social-agent growth goals set --platform youtube --account main \
    --target-followers 10000 --deadline 2026-12-31
social-agent growth audit --platform youtube --account main --followers 850 \
    --posts-per-week 3 --avg-views 4200 --avg-likes 180 --avg-comments 12 \
    --niche "AI video tutorials" --has-bio --has-avatar --has-cta

# YouTube packaging: quality gate + scored titles + descriptions
social-agent youtube titles "my sora workflow" --keyword sora
social-agent youtube preflight --title "..." --thumbnail thumb.png \
    --hook-30s --audio --retention-edit --captions --end-screen

# write like a human; BE the account owner (identity breaks are refused)
social-agent voice check --text "draft text..." --platform tiktok
social-agent identity create --account main --name "Owner Name" \
    --voice-traits "dry humor, short sentences" --opinions "thumbnails matter most"
social-agent identity check --text "draft text..." --account main

# security-conscious: scan drafts, audit state, account-anomaly watcher
social-agent security scan --text "draft text..."
social-agent security audit

# study-to-improve: journal, experiments, review-only proposals
social-agent study run --propose
social-agent study experiment start --name hook-test --kind hook \
    --a "bold claim" --b "question"
social-agent study experiment conclude --name hook-test --metric-a 4.2 --metric-b 5.9
```

Every `post draft` and `engage comment` automatically runs the content gates:
secrets → refused, identity breaks → refused, AI-ish voice → warning.

## Moderation + content production

Comment moderation (your posts only, approval-gated) and local content
production (captions, video, audio) — see guardrails §17–18:

```bash
# classify comments: ok / question / praise / spam / toxic
social-agent moderate scan --platform tiktok --account main --post v1 \
    --fixture watchers/fixtures/comments_moderation.json
# propose hiding a comment (explicit approval required, or pre-approved rule)
social-agent moderate hide --platform tiktok --account main --post v1 \
    --comment c3 --text "DM me for free crypto!!" --reason "DM scam"
social-agent moderate approve --id m-abc123
social-agent moderate done --id m-abc123

# platform-optimized captions (pass voice + identity gates)
social-agent caption generate --platform tiktok --topic "sora camera moves" \
    --tone bold --account main
social-agent caption variants --platform x --topic "sora camera moves" --n 5

# video editing via ffmpeg (only external dependency; see video/SETUP.md)
social-agent video info --input raw.mp4
social-agent video clip --input raw.mp4 --start 10 --duration 30 --output cut.mp4
social-agent video to-vertical --input cut.mp4 --output short.mp4
social-agent video frame --input cut.mp4 --at 3 --output thumb.jpg
social-agent video compress --input short.mp4 --output upload.mp4 --preset tiktok
social-agent video plan create --name ep1 \
    --steps '[{"op":"clip","start":0,"duration":20},{"op":"to-vertical"}]'
social-agent video plan run --name ep1 --input raw.mp4 --output ep1.mp4

# audio: clips, loops, ducked mixes, extraction, loudness normalization
social-agent audio clip --input song.mp3 --start 30 --duration 15 \
    --fade-in 2 --fade-out 3 --output hook.mp3
social-agent audio mix --voiceover vo.mp3 --bed music.mp3 --output final.mp3
social-agent audio normalize --input final.mp3 --output loud.mp3 --preset tiktok

# smart aspect-ratio fitting — the agent knows every platform's video spec
# (video/specs.yaml, checked 2026-09-25; human-readable video/SPECS.md).
# Default is NEVER destructive: pad (blurred fill) keeps 100% of the frame.

# AI Video Editor Worker — the full edit bench (see editor/WORKFLOW.md)
social-agent editor watch --input raw.mp4 --out work/          # mandatory first pass
social-agent editor highlights --dir work/ --top 5             # data-ranked selects
social-agent editor grade apply --input raw.mp4 --output g.mp4 --look teal-noir
social-agent editor transcribe --input raw.mp4 --dir work/      # whisper or heuristic
social-agent editor captions --input g.mp4 --srt work/captions.srt --style pop \
    --output captioned.mp4
social-agent editor broll-plan --dir work/ --broll cutaway.mp4 --out work/broll.json
social-agent editor project --kind kdenlive --title ep1 \
    --spec '{"assets":["captioned.mp4"],"clips":[{"asset":"captioned.mp4"}]}' \
    --out ep1.kdenlive                                         # open in Kdenlive GUI
social-agent editor brand create --label main                  # colors/logo/grade kit
social-agent editor brand apply --input captioned.mp4 --output branded.mp4 --label main
social-agent editor batch --op grade --look neon-city --in "raw/*.mp4" --out graded/
social-agent editor queue add --name ep1 --cmd "ffmpeg -y -i branded.mp4 ep1.mp4"
social-agent editor queue run --resume                         # crash recovery
social-agent editor qa --input ep1.mp4                         # verifies the render
social-agent editor thumb --input ep1.mp4 --text "Hook text" --output thumb.jpg
social-agent editor export --input ep1.mp4 --output master.mp4 --resolution 4k --codec hevc
social-agent editor motion lower-third --text "Nova" --output lt.png
social-agent video fit --input cut.mp4 --output short.mp4 --for tiktok
social-agent video fit --input wide.mp4 --output short.mp4 --for youtube:shorts --dry-run
# crop-to-fill ONLY with an explicit focus point (--focus center|top|bottom|face);
# without one, crop is refused. The agent tells you what WILL be cut first.
social-agent video fit --input wide.mp4 --output short.mp4 \
    --for tiktok --crop --focus face
# pre-post gate: PASS/FAIL against the spec, with concrete fixes
social-agent video preflight --input short.mp4 --for youtube:shorts
# post draft with a video runs the spec preflight and REFUSES the draft on FAIL
social-agent post draft --platform tiktok --account main \
    --text "new tutorial is up" --video short.mp4
```

Every video/audio command prints the exact ffmpeg invocation before running
(`--dry-run` previews without executing) and refuses to overwrite inputs.
Audio operates on files **you provide** — use platform-licensed music
libraries or your own audio (see `audio/MUSIC.md`).

## Operations: approvals, people, rate limits, crisis, listener

Five operational capabilities, one guard order
(**ToS > crisis > approvals > rate limits > quiet hours**):

```bash
# 1. one approval queue for everything (pending/approved/rejected/held/rate_limited)
social-agent engage like --platform tiktok --account main --target v1
social-agent approvals list                 # review the single queue
social-agent approvals approve --id q-abc   # executes the underlying action
social-agent approvals reject --id q-abc --reason "too salesy"
social-agent approvals policy               # per-type require/auto (default: require)

# 2. people memory: recurring followers & conversations
social-agent people top --account main
social-agent people show --account main curious_cat
social-agent people note --account main curious_cat "asked about background blur"
social-agent people tag --account main curious_cat top-fan

# 3. central rate-limit controller (per platform+action, sliding windows)
social-agent ratelimit status               # remaining quota per bucket
social-agent ratelimit config               # effective limits
# exhausted bucket -> exit 2, action queued as rate_limited with retry_at (never dropped)

# 4. crisis mode: the kill switch (never auto-resumes)
social-agent crisis on --reason "viral backlash brewing"
social-agent crisis status
social-agent crisis off                     # explicit only; held items re-pend for approval

# 5. notification listener: fast polls, careful routing
social-agent listen once                    # single pass over notification/comment/DM watchers
social-agent listen --interval 60           # continuous (Ctrl-C to stop)
# questions -> reply draft (voice+identity gated) queued for approval
# toxic/spam -> hide proposal; DMs -> people memory + user notification
```

## Heartbeats

Every watcher run emits `<base>/<watcher-id>/start`, then success or `/fail`
(the same protocol as the heartbeat repo). The supervisor daemon emits its
own heartbeat every 10s:

```bash
social-agent heartbeat status
social-agent heartbeat daemon --once --watchers <id>
```

With no `base_url` in `heartbeat.yaml`, pings are recorded locally to
`heartbeat.json` (log-only, zero network). See `docs/heartbeat-integration.md`
for pairing with the heartbeat repo's cron wrapper and daemon.

## Architecture

```
bin/social-agent        CLI (accounts, watch, post, engage, mission, autonomy,
                        profile, heartbeat, research, analytics, doctor,
                        growth, youtube, voice, security, study, identity,
                        moderate, caption, video, audio, editor,
                        approvals, people, ratelimit, crisis, listen)
watchers/               poll-based monitors; check() -> structured events (read-only)
  framework.py          base class: config schema, state, idempotent dedupe, events.jsonl
  notification|comment|feed|follow|activity|channel|message _watcher.py
  trend|competitor|sentiment|mention|velocity|content-idea|crisis|security _watcher.py
  fixtures/             sample JSON feeds so everything runs offline
approvals/              unified human approval queue (pending/approved/rejected/held/rate_limited)
people/                 people memory: interaction scores, notes, tags, top fans
ratelimit/              central per-(platform,action) sliding-window controller
crisis/                 crisis mode: global kill switch, never auto-resumes
listen.py               fast-poll listener routing comments/DMs/notifications
engagement/             interest scoring (interests profile) + anti-spam guards
growth/                 organic playbooks, follower goals, 5-pillar audits,
                        YouTube packaging (titles, descriptions, preflight gate)
voice/                  human-sounding style: banned AI-isms, per-platform
                        profiles, `check_text` (warns below score 60)
identity/               embodiment: per-account personas; the agent IS the owner
                        (never claims to be an AI — breaks are refused)
security/               secret detection (refuses secret-shaped drafts),
                        state audits, checklist, security checklist
learning/               study-to-improve: journal, A/B experiments, review-only
                        proposals (never auto-applied)
missions.py / autonomy.py
                        mission files (area of work) + scoped autonomy grants
heartbeat/              protocol-compatible ping client (stdlib); heartbeat.yaml config
platforms/              per-platform adapter specs + capabilities.md matrix
policy/                 guardrails.md (human) + policy.yaml (machine, parsed by yaml_lite.py)
catalogs/               curated tools / schedulers / analytics / official APIs (38 links, verified)
skills/social-agent/    SKILL.md so any agent can install and use this
tests/                  pytest suite (CLI e2e, watcher units, policy enforcement)
exams/                  scenario exams, all recorded in RESULTS.md
docs/                   heartbeat-integration.md
missions/               example mission file
```

**Data flow:** watcher poll → `events.jsonl` → `analytics` summarizes; proposals
(`actions.json`, `queue.json`) move `proposed → approved → done` only through
explicit commands (or autonomous auto-approval inside mission scope). Rate
limits, spam guards (`policy.yaml`), and quiet hours are enforced on every
acting operation; violations exit with code 2 and a `REFUSED` message, and
refusals are logged with reasons.

## Safety model

Read `policy/guardrails.md`. In short:

- Watchers never act. There is no code path from a watcher to a post/like.
- Every acting operation needs its own approval record (expires after 24h) —
  or a scoped autonomous grant.
- Selective engagement: likes/follows only for interesting content; per-author
  cooldowns and like caps block spam patterns.
- Profile changes always need explicit approval — no exceptions.
- Conservative per-platform hourly/daily caps; the CLI refuses over-cap actions.
- No credentials in the repo or in state — sign-in happens in your own browser.
- Prohibited by design: mass follow/unfollow, comment spam, astroturfing.
- Growth is organic-only and sits under the ToS layer (guardrails §13):
  playbooks inform content choices, they never authorize acting operations.
- Content gates on every `post draft` / `engage comment`: secret detection
  refuses secret-shaped drafts; the identity check refuses drafts that break
  embodiment (claiming to be an AI); the voice check warns on AI-ish style.
  Refusals exit with code 2 and are logged to `refusals.jsonl`.
- The agent writes **as the account owner** (guardrails §14): first person,
  owner's name and voice, never "I'm an AI". Personas live in
  `<home>/identity/accounts/<label>.md` (`identity create/show`).
- Security-conscious: no secrets in state (audited by `security audit`),
  and a security watcher fires urgent events on follower purges, mass
  unfollows, or unknown login sessions (guardrails §15).
- Per-platform Terms of Service are the ceiling: `platforms/tos.py` checks
  every acting operation and watcher poll against `platforms/<name>/tos_rules.yaml`
  *before* missions, autonomy, quiet hours, and rate limits. A ToS-prohibited
  action is refused (exit 2) and logged — no mission or approval can override
  it. See `policy/guardrails.md` §12 and each platform's `terms.md`.

## Honest limitations

- **The CLI never performs a live action.** Posting/liking/commenting happen in
  a real browser session driven by you or your agent; the CLI proposes,
  gates, and logs.
- **No streaming.** Watchers poll on an interval you choose; there is no
  realtime push.
- **Platform gaps are documented, not hidden** — see `platforms/capabilities.md`
  (e.g. no public write API for TikTok/Instagram personal accounts, YouTube's
  10k-units/day quota, X's paid API tiers).
- **X's terms prohibit non-API automation outright**, and this tool is
  browser-driven: automated likes, comments, follows, reposts, DMs, and
  browser-based data collection on X are refused by the CLI rather than
  faked. The sanctioned path is X's official API.
- Fixture-based offline mode is for development and tests; live reading needs a
  logged-in browser session or official API credentials you create yourself.

## Tests & exams

```bash
python3 -m pytest tests/ -q        # pytest suite
python3 exams/run_exams.py         # scenarios -> exams/RESULTS.md
```
