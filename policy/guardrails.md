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
- `analytics` summarizes this log; nothing is silently dropped.
