# social-agent

An autonomous social-media monitoring toolkit for AI agents. Poll-based
watchers observe TikTok, X, Instagram, Facebook, YouTube, Reddit, and LinkedIn and
**propose** actions; acting (post, like, comment, follow, retweet, DM) is
dry-run by default and requires explicit per-action approval. Approved
proposals become structured **execution tickets** fulfilled live in the
external agent's own browser (see `docs/HOST_BROWSER.md`). Pure Python
stdlib — no dependencies, no binaries, no credentials stored.

## Install

```bash
git clone https://github.com/kilomene/social-agent.git ~/workspace/social-agent
cd ~/workspace/social-agent && ./install.sh   # creates ~/SocialAgent/ (its own brain)
export SOCIAL_AGENT_HOME=~/SocialAgent
export PATH="$HOME/workspace/social-agent/bin:$PATH"
social-agent doctor
```

Requirements: Python 3.8+, stdlib only (no pip packages needed).
`install.sh` is idempotent — re-run it to top up a workspace, or
`install.sh --home <dir>` for another isolated install. State lives in
`~/SocialAgent` (override with `SOCIAL_AGENT_HOME`; the old default
`~/.social-agent` still works).

## Quickstart

```bash
# register an account (handle only — never a password)
social-agent accounts add --platform tiktok --username somehandle --label main

# start watchers (fixtures make everything work offline)
social-agent watch start --type notification --platform tiktok --account main \
    --fixture core/watcher_engine/fixtures/notifications.json
social-agent watch start --type trend --platform tiktok --account main \
    --set use_interest_profile=true --fixture core/watcher_engine/fixtures/trend.json

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
    --fixture core/watcher_engine/fixtures/comments_moderation.json
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

## Permanent memory, backups, crash recovery

The agent remembers everything in `<home>/memory.db` (SQLite) and
backs itself up automatically (`<home>/backups/`, content-addressed
snapshots). Every acting intent is journaled (`<home>/audit/journal.jsonl`)
before execution so a crash can be resumed safely — `recover` verifies
each unfinished intent against real state and **never repeats** one that
already completed (no duplicate posts).

```bash
social-agent memory query "SELECT label FROM accounts"   # SELECT-only, enforced
social-agent memory remember "post daily" --by user --why "consistency"
social-agent memory recall
social-agent memory relate brand:nova owns account:main  # relationship graph
social-agent memory graph brand:nova
social-agent memory sop add "weekly review" --body "# review"
social-agent backup list                                  # snapshots w/ triggers
social-agent backup diff <snap1> <snap2>
social-agent backup restore <snap>              # dry-run plan by default
social-agent backup restore <snap> --apply      # stages only; never overwrites live files
social-agent recover                            # replay the journal after a crash
social-agent recover --execute                  # also re-execute safe local renders
```

## Execution: execution tickets + the external agent's live browser

**social-agent is the brain; the external agent is the hands.** The repo
proposes, gates, and logs — it never drives a platform itself. No APIs,
no API keys, and no bundled browser automation (no Playwright/Chromium,
no persistent profiles owned by the repo).

Approving a proposal issues a machine-readable **execution ticket**
(lifecycle: `issued → claimed → fulfilled`):

```bash
social-agent tickets                          # list execution tickets
social-agent ticket show <ticket-id> --json   # machine-readable ticket JSON
# ... the external agent (Muse) claims the ticket and fulfills it LIVE in
# its own browser — the browser card the user watches ...
social-agent ticket claim <ticket-id> --agent Muse --session <session-id>
social-agent ticket fulfill <ticket-id> --evidence "posted, https://..."  # idempotent
social-agent ticket cancel <ticket-id> --reason "..."   # withdraw a ticket
```

- A plan executes **at most once**: the event journal carries an
  idempotency key per plan, so a crash mid-execution resumes instead of
  repeating (no duplicate posts).
- If a step fails, the host records the failure as evidence and does
  **not** retry blindly — the plan is re-planned or decided by a human.
- The plan's steps were ToS-checked at approval time; the host must not
  improvise out-of-scope actions. See `docs/HOST_BROWSER.md`.

**ToS honesty:** X browser-driven engagement is `prohibited` by default
(X requires API-only automation) and fails closed. Explicit opt-in only:
`tos.acknowledged_risk: [x]` in policy.yaml downgrades it to restricted
with a loud logged advisory (account suspension/ban risk) recorded in
`audit/tos_acknowledgments.jsonl`. Without the acknowledgment, the
prohibition stands — the agent never silently violates terms.

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
core/watcher_engine/    SINGLE watcher engine: lifecycle, scheduling, event dispatch,
                        crash recovery (checkpoints live in the shared memory DB)
  engine.py             register/enable/disable/poll/poll_platform/poll_all;
                        duplicate registration refused (DuplicateWatcherError)
  framework.py          Watcher base: config schema, idempotent dedupe, checkpoints,
                        event-bus dispatch (events.jsonl kept as legacy mirror)
  watchers/             the 15 watcher classes, exactly once (no per-platform copies)
  fixtures/             sample JSON feeds so everything runs offline
platforms/<name>/       per-platform tree — registration + views ONLY, never shared core
  __init__.py           adapter spec (declarative, no-API: execution via execution tickets
                        in the external agent's live browser)
  terms.md / tos_rules.yaml
                        per-platform ToS (fail-closed; checked first in the guard order)
  watchers/             REGISTRATION manifest (which watchers + defaults)
  memory/               namespaced VIEW into the shared DB (no .db copy)
  workspace/            shipped workspace template (workspace.yaml + state/)
                        shipped: tiktok, x, instagram, facebook, youtube, reddit, linkedin, threads
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
catalogs/               curated tools / schedulers / analytics links (browser-only;
                        no API catalog — removed per the owner's explicit order)
skills/social-agent/    SKILL.md so any agent can install and use this
tests/                  pytest suite (CLI e2e, watcher units, policy enforcement)
exams/                  scenario exams, all recorded in RESULTS.md
docs/                   HOST_BROWSER.md (host execution model), platform-workspaces.md,
                        heartbeat-integration.md, listen-latency.md
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
- No credentials in the repo or in state — logins live ONLY in the host's
  Secure Vault, and sign-in in the host's live Chromium goes through the
  vault-backed browser flow with the user's approval. The agent never
  sees or handles raw passwords, tokens, or 2FA codes.
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

- **The CLI never performs a live action.** Posting/liking/commenting are
  performed by the external agent in its own live browser via approved
execution tickets (see `docs/HOST_BROWSER.md`); the CLI proposes, gates, and logs.
- **No streaming.** Watchers poll on an interval you choose; there is no
  realtime push.
- **No-API by design.** There are no API clients, no API keys, and no
  API backend anywhere in this repo — every platform action is performed
  in the external agent's live browser. The external agent's live browser is not an
  API. There is no config switch to change this; `platforms/<name>/backend`
  does not exist as a concept.
- **Platform gaps are documented, not hidden** — see `platforms/capabilities.md`.
- **X's terms prohibit non-API automation outright**, and this tool
  performs through a live browser by the owner's explicit order:
  browser-driven likes, comments, follows, reposts, DMs, and data
  collection on X are refused by the CLI rather than faked. They proceed
  only under the explicit `tos.acknowledged_risk: [x]` opt-in, which
  records the owner's informed acceptance of the suspension risk.
- Fixture-based offline mode is for development and tests; live reading
  needs the host's logged-in browser session.

## Tests & exams

```bash
python3 -m pytest tests/ -q        # pytest suite
python3 exams/run_exams.py         # scenarios -> exams/RESULTS.md
```
