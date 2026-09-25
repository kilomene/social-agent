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
