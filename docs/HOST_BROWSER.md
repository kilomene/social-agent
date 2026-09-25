# Host-browser execution

**social-agent is the BRAIN. The external agent is the HANDS.**

social-agent runs on the host agent's computer (Muse) as the brain: it
watches, proposes, gates, and logs — watchers, the proposal engine, the
approval queue, the rate-limit controller, the permanent memory (SQLite),
the event journal, the ToS engine, missions, the growth engine, content
production (video/audio editing, captions), backup/recovery, and
heartbeat. It does not, and must not, touch a social platform itself.

The **external agent** (e.g. Muse with its own server-side Chromium) is
the hands: when the user approves a proposal, the approval issues a
machine-readable **execution ticket** (JSON: action, platform, account,
target, parameters, idempotency key, plus the ToS/approval/rate-limit
receipts), and the external agent fulfills the ticket **visibly in its
own browser** — the live browser card the user watches. The repo does
not bundle, download, install, or drive its own Playwright/Chromium,
persistent browser profiles, or any separate browser automation. There
is no `browser/login/act` automation surface in this repo.

## The ticket lifecycle

```
issued → claimed → fulfilled
   \-> cancelled      \-> failed
```

- **`social-agent tickets`** — list execution tickets (status
  filterable; `--json` emits raw ticket JSON).
- **`social-agent ticket show <id> [--json]`** — show one ticket:
  action, platform, account, target, parameters, the
  ToS/approval/rate-limit receipts, and its step-by-step browser
  instructions written for the external agent to follow visibly in its
  live browser. `--json` emits the machine-readable ticket the
  external agent consumes.
- **`social-agent ticket claim <id> --agent <name> --session <id>`** —
  the external agent claims the ticket, recording which agent + live
  session is doing the work. A ticket can be claimed by exactly one
  session at a time; the claim is refused if the ticket is already
  claimed or fulfilled.
- **`social-agent ticket fulfill <id> --evidence <note>`** — the
  external agent records fulfillment with an evidence note (what was
  done, where — a URL, timestamp, or screenshot reference). This step
  is **idempotent**: a ticket can never be fulfilled twice. The event
  journal carries an idempotency key per ticket; if the external agent
  crashes mid-execution, replay verifies against real state and
  **skips** work that already completed — it is never repeated. No
  duplicate posts. The operator then confirms via the existing
  `engage done` / approval flow.
- **`social-agent ticket fail <id> --error ...`** — the external agent
  reports the ticket could not be completed.
- **`social-agent ticket cancel <id> --reason ...`** — withdraws a
  ticket that should not go ahead; the reason is logged.

## Who performed what

`identity/host_sessions/` records which external agent + live session
fulfilled each execution ticket, with the evidence note from
`ticket fulfill`. There is no shared persistent browser profile in the
identity store — execution happens in the external agent's own live
browser, and the record of it lives here.

## Credentials — logins live in the secure vault, never in the repo

All social-platform logins/credentials live **only** in the agent's
secure vault (or the user's own browser). The social-agent repo
**never stores, logs, or handles raw credentials** — no credential
fields in the memory DB, in tickets, in logs, or in identity files
(there is a test asserting this: no password/token/secret/key fields
in the ticket schema or stored ticket JSON). This strengthens, not
replaces, the standing rule that the agent never touches passwords,
tokens, or 2FA: the agent itself never sees them.

When the external agent needs to act logged-in in its live browser,
sign-in goes through the **vault-backed browser flow with the user's
approval**. The browser session is the user's own live logged-in
session; login state already exists there. If the session is logged
out, the external agent asks the user and completes sign-in through
the vault-backed flow — the agent (and the repo) never handles a raw
password or token, and it never attempts a 2FA bypass. A 2FA/challenge
screen means: pause, notify the user, wait.

## If a step fails

Record the failure as evidence and stop. Run
`ticket fail <id> --error "<what happened>"` with a concrete failure
note (error text, screenshot, URL) — but **never retry blindly**. A
failed step that is retried without understanding is how accounts get
suspended and actions get duplicated. The idempotency guarantee means
a partially completed ticket can be safely resumed by a new ticket or
a human decision — not by re-running the failed step on autopilot.

## ToS reminder

The ticket's steps were **ToS-checked at approval time** — the ToS
engine runs before quiet hours, rate limits, mission scope, and
autonomy, and it fails closed (see `policy/guardrails.md` §12 and
`platforms/<name>/terms.md`); the receipts on the ticket prove it. The
external agent must **not improvise out-of-scope actions** while
fulfilling: follow the ticket's steps, and nothing else. If the live
page suggests a different action (a recommended follow, a suggested
post, an upsell), it is out of scope — record it as an observation
for a new proposal instead of acting.

Note for X specifically: X's terms prohibit non-API automation
outright, so X tickets that involve browser-driven likes, comments,
follows, reposts, DMs, or data collection are refused by default. They
proceed only under the explicit `tos.acknowledged_risk: [x]` opt-in in
`policy/policy.yaml`, which records the owner's informed acceptance
of the suspension risk (see the ToS/host-browser section in
`policy/guardrails.md`).

## Related docs

- `policy/guardrails.md` — the full safety policy (ToS is the ceiling).
- `policy/policy.yaml` — machine-readable policy, incl. the
  `host_execution:` section (active hours) and `tos.acknowledged_risk`.
- `identity/guide.md` — identity/embodiment rules; the agent writes as
  the account owner, never as an AI.
