---
name: "social-agent"
description: "Autonomous social-media monitoring toolkit: 14 poll-based watchers (notifications, comments, feed, follows, activity, channels, messages, trends, competitors, sentiment, mentions, velocity, content-ideas, crisis) plus approval-gated posting, selective engagement (like/follow only what's interesting, spam-guarded), scoped autonomous missions, and protocol-compatible heartbeats across TikTok, X, Instagram, Facebook, YouTube, Reddit. Watchers observe and propose; acting requires explicit per-action approval or a scoped autonomy grant. Pure stdlib, works offline."
---

# social-agent skill

Install and use the social-agent toolkit from the `social-agent` repo.

## Install

```bash
git clone <repo-url> ~/workspace/social-agent
export PATH="$HOME/workspace/social-agent/bin:$PATH"
export SOCIAL_AGENT_HOME="$HOME/.social-agent"   # state dir (default)
social-agent doctor
```

Requirements: Python 3.8+, nothing else (pure stdlib).

## Safety model (read policy/guardrails.md first)

- Watchers are **read-only**: they poll, detect, and *propose* — never act alone.
- `post` / `engage` create **dry-run proposals**; each needs an explicit
  `approve` before anything may be performed, and performance happens in a real
  browser session, logged with `engage done`.
- **Selective engagement**: likes/follows only for posts/users scoring as
  interesting against the `interests:` profile; anti-spam guards (like caps,
  per-author cooldown, min gap, follow caps) refuse spam patterns with reasons.
- **Autonomous mode** is off by default; grant per-mission with
  `autonomy grant --mission <name> --confirm`. In-scope actions auto-approve;
  out-of-scope actions are blocked and logged.
- **Profile changes always need explicit `profile approve`** — no exceptions,
  even in autonomous mode.
- Per-platform rate limits and quiet hours are enforced by the CLI and refuse
  with exit code 2.
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
```

## Watcher types (14)

`notification` `comment` `feed` `follow` `activity` `channel` `message`
`trend` (trending topics filtered by interests) `competitor` (rival cadence +
deltas digest) `sentiment` (sentiment-shift alerts) `mention` (unified
@mentions) `velocity` (viral-velocity early alerts) `content-idea` (repeated
audience questions → video ideas) `crisis` (negative-spike urgent alerts)
— see `watchers/` for each config schema.

## Environment overrides (for tests)

- `SOCIAL_AGENT_HOME` — state directory.
- `SOCIAL_AGENT_POLICY` — alternate policy.yaml (e.g. to test quiet hours).
- `SOCIAL_AGENT_HEARTBEAT` — alternate heartbeat.yaml.
- `SOCIAL_AGENT_MISSIONS` — alternate missions directory.

## What it cannot do

See `platforms/capabilities.md` for the honest per-platform matrix. The CLI
never posts/likes/comments by itself; live execution is always a real browser
session with the user's own sign-in. Docs: `docs/heartbeat-integration.md`.
