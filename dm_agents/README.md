# dm_agents — DM Conversation Agents

One agent per (platform, account). The DM agent **owns that account's DM
threads exclusively** — the poll-based message watchers
(`tiktok:message`, `x:message`, `instagram:message`, `facebook:message`)
were retired (2026-09-25) so a watcher and a DM agent can never
double-handle the same conversation.

## The tick/report loop (brain ⇄ hands)

The brain never drives a browser. Each check is two beats:

1. **`dm-agent tick`** (brain) — decides whether a check is due and, if
   so, issues a read-only `dm_check` execution ticket plus
   machine-readable hands instructions: the threads to open and each
   thread's `last_seen_id` cursor, plus exact step-by-step browser steps.
2. **Host agent (Muse, live Chromium)** — opens the DM inbox, reads the
   threads (read-only; never replies, never opens links), and returns
   the observed-messages JSON.
3. **`dm-agent report --messages '<json>'`** (brain) — ingests what the
   host saw, diffs against each thread's `last_seen_id` (inbound messages
   only, oldest → newest), duplicate-guards, drafts style-gated replies,
   and queues them in the approvals queue.

Replies go out ONLY through the standard pipeline:
**ToS → crisis → approvals → rate limits → quiet hours.** A `dm_send`
ticket is minted when the approval item is approved — not by the agent.

## Trigger contract: detection is event-driven, not poll-bound

The scheduled poll is the **backstop**, not the detector.
`dm-agent tick` accepts an external trigger source:

```
dm-agent tick --platform x --account main --trigger <source>
```

`<source>` is a free-form label recording what kicked off the check:
- `schedule` — the cron/routine poll (default)
- `gmail-notification` — a platform notification email arrived
- `manual` — the operator (or host agent) kicked it off directly

A triggered tick **jumps the queue**: it runs immediately regardless of
`poll_interval` timing. It never jumps the **pile-up guard**: if a
previous `dm_check` is still in flight (ticket issued/claimed, not yet
fulfilled), the triggered tick is skipped with
`"skipped": "previous check in flight"`. This is the never-pile-up rule —
checks can arrive faster than the host's browser sessions can run them,
so concurrency is strictly one in flight per (platform, account).

### Host-side notification watch (not repo code)

The repo ships no Gmail watcher — the runtime is host-side. The contract
the host runtime implements:

1. The host runs a **lightweight Gmail notification-email watch every few
   minutes** (its own code, outside this repo).
2. On any DM/platform notification email for an account with an active
   DM agent, the host fires:
   `dm-agent tick --platform <p> --account <a> --trigger gmail-notification`
3. The tick runs immediately (jumping the poll queue, still respecting
   the pile-up guard), the host reads the DMs in its live Chromium, and
   `dm-agent report` drafts replies — so a new DM is detected and drafted
   **within minutes, not within one poll cycle**.

If the email watch misses (no email, wrong label, host down), the
scheduled poll still catches the message on its next cycle. The poll is
the backstop; triggers are the fast path.

### Cadence

| Knob | Value | Notes |
|---|---|---|
| `poll_interval` | default **600s**, hard minimum 300s (clamped) | scheduled backstop cadence |
| `target_interval` | **35** (aspiration, recorded not enforced) | the owner's stated goal; each check needs a multi-minute live browser session, so tighter loops would outrun the hands — the 600s default stands |
| `stop_after_idle_hours` | default 48 | threads idle longer are parked (no longer checked) until new inbound unparks them |

## CLI

```
dm-agent list                                    # platforms + adapter readiness
dm-agent start --platform x --account main
dm-agent stop  --platform x --account main --reason "..."
dm-agent status --platform x --account main
dm-agent tick   --platform x --account main [--trigger gmail-notification]
dm-agent report --platform x --account main --messages '<json>'
```

`tick` prints machine-readable JSON (ticket id + instructions). `report`
prints what was processed per thread: new inbound count, drafts queued,
ToS refusals, rate-limited items, and the fulfilled ticket id.

## Observed-messages JSON contract (what `report` ingests)

```json
{
  "threads": [
    {"thread_id": "conv-1",
     "messages": [
       {"id": "m1", "from": "them", "text": "hey", "ts": 1790348600},
       {"id": "m2", "from": "me",   "text": "hey!", "ts": 1790348610}
     ]}
  ]
}
```

`from` is `"them"` (inbound) or `"me"` (outbound); `ts` is a unix
timestamp (0 if unknown). Messages are normalized oldest-first; the
agent compares against each thread's `last_seen_id` and processes only
new inbound messages. First sight of a thread replies only to messages
from the last 24h — old history is marked seen, not replied to.

## Per-platform status (2026-09-25)

| Platform | Status | Notes |
|---|---|---|
| **x** | ready | `dm_check` (automated_reading: restricted, low-volume own-account) works; `dm_send` is **prohibited** on X — refusals surface, never bypassed |
| **tiktok** | refused | DM message content is app-only, not visible in the web client (verified live 2026-09-25). Parks TikTok rather than pretend to read DMs |
| **instagram** | stub | not configured: no account registered, no verified web DM flow |
| **facebook** | stub | not configured: no account registered, no verified web DM flow |

Encrypted-messages passcode: if the platform asks for one during a check,
the hands instructions say STOP and report — the passcode is never typed
and never asked for in this flow.

## Style rules (enforced by the style gate, user's verbatim spec)

- No em dashes — split into two sentences. No spaced en dashes — comma.
- Short, plain sentences (>24 words split at natural joints). Contractions fine.
- Banned: "I hope this helps", "certainly", "as an AI", "hope this", "feel free", "delve", "leverage", "furthermore".
- Text is the default. A voice note / image / video goes out ONLY when the
  correspondent explicitly asks for one — and the repo has no TTS, image,
  or video generation, so media requests get an honest plain-language
  fallback inside the reply text (never silence, never a fake promise).
- Reply to every new inbound message in one cycle. No batching, no "I'll
  get back to you later".

## Stop conditions

- Explicit `dm-agent stop --reason`.
- Idle threads park after `stop_after_idle_hours` (default 48h); new
  inbound unparks automatically.
- Agent-level state (`active`, `stop_reason`, `last_cycle`,
  `pending_check`) lives in the `dm_agent_state` table — every write is
  journaled, so cursors survive restarts and are captured by backups.

## Upgrade note (existing installs)

The retired watchers may still be registered in a live brain. Stop them:

```
social-agent watch stop x:message tiktok:message instagram:message facebook:message
```

Also remove `tiktok:message` from any cron watcher-loop task definitions
(e.g. the TikTok 30-minute watcher loop now runs 13 watchers).
