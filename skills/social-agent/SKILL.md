---
name: "social-agent"
description: "Autonomous social-media monitoring toolkit: poll-based watchers (notifications, comments, feed, follows, activity, channels, messages) plus approval-gated posting and engagement across TikTok, X, Instagram, Facebook, YouTube, Reddit. Watchers observe and propose; acting requires explicit per-action approval. Pure stdlib, works offline."
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
social-agent watch start --type comment --platform tiktok --account main \
  --set post_id=vid123 --fixture watchers/fixtures/comments.json

# 3. Poll
social-agent watch run <watcher-id>
social-agent watch events --limit 10

# 4. Propose engagement (dry-run), approve, then log after browser execution
social-agent engage like --platform tiktok --account main --target vid123
social-agent engage list --status proposed
social-agent engage approve <action-id>
# ... perform the like in a real browser session ...
social-agent engage done <action-id> --result "liked in browser session"

# 5. Draft and approve posts
social-agent post draft --platform tiktok --account main --text "Hello world"
social-agent post approve <post-id>

# 6. Research + analytics
social-agent research "AI video" --platforms tiktok,x
social-agent analytics --days 7
```

## Watcher types

`notification` `comment` `feed` `follow` `activity` `channel` `message`
— see `watchers/` for each config schema.

## Environment overrides (for tests)

- `SOCIAL_AGENT_HOME` — state directory.
- `SOCIAL_AGENT_POLICY` — alternate policy.yaml (e.g. to test quiet hours).

## What it cannot do

See `platforms/capabilities.md` for the honest per-platform matrix. The CLI
never posts/likes/comments by itself; live execution is always a real browser
session with the user's own sign-in.
