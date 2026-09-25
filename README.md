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
                        growth, youtube, voice, security, study, identity)
watchers/               poll-based monitors; check() -> structured events (read-only)
  framework.py          base class: config schema, state, idempotent dedupe, events.jsonl
  notification|comment|feed|follow|activity|channel|message _watcher.py
  trend|competitor|sentiment|mention|velocity|content-idea|crisis|security _watcher.py
  fixtures/             sample JSON feeds so everything runs offline
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
