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
social-agent watch start --type comment --platform tiktok --account main \
    --set post_id=vid123 --fixture watchers/fixtures/comments.json

# poll + review
social-agent watch run <id>
social-agent watch events --limit 10

# propose engagement (dry-run), approve, perform in browser, log it
social-agent engage like --platform tiktok --account main --target vid123
social-agent engage approve <action-id>
# ... do it in a real browser session ...
social-agent engage done <action-id> --result "liked in browser session"

# drafts need approval too
social-agent post draft --platform tiktok --account main --text "Hello"
social-agent post approve <post-id>

# research plans + analytics
social-agent research "AI video" --platforms tiktok,x
social-agent analytics --days 7
```

## Architecture

```
bin/social-agent        CLI (accounts, watch, post, engage, research, analytics, doctor)
watchers/               poll-based monitors; check() -> structured events (read-only)
  framework.py          base class: config schema, state, idempotent dedupe, events.jsonl
  notification|comment|feed|follow|activity|channel|message _watcher.py
  fixtures/             sample JSON feeds so everything runs offline
platforms/              per-platform adapter specs + capabilities.md matrix
policy/                 guardrails.md (human) + policy.yaml (machine, parsed by yaml_lite.py)
catalogs/               curated tools / schedulers / analytics / official APIs (38 links, verified)
skills/social-agent/    SKILL.md so any agent can install and use this
tests/                  25 pytest tests (CLI e2e, watcher units, policy enforcement)
exams/                  6 scenario exams, 22/22 recorded in RESULTS.md
```

**Data flow:** watcher poll → `events.jsonl` → `analytics` summarizes; proposals
(`actions.json`, `queue.json`) move `proposed → approved → done` only through
explicit commands. Rate limits (`policy.yaml`) and quiet hours are enforced on
every acting operation; violations exit with code 2 and a `REFUSED` message.

## Safety model

Read `policy/guardrails.md`. In short:

- Watchers never act. There is no code path from a watcher to a post/like.
- Every acting operation needs its own approval record (expires after 24h).
- Conservative per-platform hourly/daily caps; the CLI refuses over-cap actions.
- No credentials in the repo or in state — sign-in happens in your own browser.
- Prohibited by design: mass follow/unfollow, comment spam, astroturfing.

## Honest limitations

- **The CLI never performs a live action.** Posting/liking/commenting happen in
  a real browser session driven by you or your agent; the CLI proposes,
  gates, and logs.
- **No streaming.** Watchers poll on an interval you choose; there is no
  realtime push.
- **Platform gaps are documented, not hidden** — see `platforms/capabilities.md`
  (e.g. no public write API for TikTok/Instagram personal accounts, YouTube's
  10k-units/day quota, X's paid API tiers).
- Fixture-based offline mode is for development and tests; live reading needs a
  logged-in browser session or official API credentials you create yourself.

## Tests & exams

```bash
python3 -m pytest tests/ -q        # 25 tests
python3 exams/run_exams.py         # 6 scenarios -> exams/RESULTS.md
```
