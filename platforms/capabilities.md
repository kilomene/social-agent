# Platform capabilities matrix

Honest summary of what social-agent can do per platform. "Browser" means a real
logged-in browser session in the account's persistent profile, driven by the
user or their agent. There is no API backend: no API clients, no API keys, no
OAuth apps — this repo contains zero platform-API integrations by the account
owner's explicit order.

| Capability | TikTok | X | Instagram | Facebook | YouTube | Reddit |
|---|---|---|---|---|---|---|
| Read feed / timeline | browser | browser | browser | browser | browser | browser |
| Read profile + follower counts | browser | browser | browser | browser | browser | browser |
| Read comments | browser | browser | browser | browser | browser | browser |
| Read notifications | browser | browser | browser | browser | browser | browser |
| Read DMs | browser | browser | browser | browser | n/a | browser |
| Post content | browser | browser | browser | browser | browser | browser |
| Like | browser | browser | browser | browser | browser | upvote: refused (vote manipulation) |
| Comment / reply | browser | browser | browser | browser | browser | browser |
| Follow / subscribe | browser | browser | browser | browser | browser | browser |
| Repost / retweet / share | browser (share) | browser | share to story via browser | browser (share) | n/a | crosspost via browser |
| DM send | browser (throttled) | browser | browser | browser | n/a | browser |

## Auth notes

- **Browser session** is the only path everywhere: the user signs in with
  their own browser in a headed first login; social-agent never sees the
  password and never stores credentials.
- There is no alternative auth path. Any `backend`, `api_key`, `api_secret`,
  or OAuth config for a social platform is not supported and never was
  shipped.

## Rate limits enforced by social-agent

See `policy/policy.yaml` (`rate_limits`). The CLI refuses acting operations
past the per-hour/per-day caps regardless of platform headroom. Every browser
action flows through the central rate-limit controller — the browser is a
backend, not a bypass.

## Terms of Service compliance (per-platform)

Each platform ships `platforms/<name>/terms.md` (human-readable rules with
official source links and a last-checked date) and `platforms/<name>/tos_rules.yaml`
(machine-readable: `prohibited` / `restricted` / `allowed` per action class,
enforced by `platforms/tos.py`).

The ToS layer runs **first** — above missions, autonomy, approvals, quiet
hours, and rate limits. A `prohibited` entry refuses the action outright
(exit 2, logged to `refusals.jsonl`); a `restricted` entry proceeds but prints
the platform's constraint as an advisory. No mission or approval can override
a prohibition.

Key platform-specific outcomes (see each `terms.md` for sources):

- **X is the strict case.** X's developer guidelines require automation only
  through the official X API and prohibit non-API automation. This tool is
  browser-driven by the owner's explicit order, so automated likes, comments,
  follows, reposts, DMs, and browser-based data collection are **prohibited**
  on X. They proceed only under the explicit `tos.acknowledged_risk: [x]`
  opt-in, which downgrades the prohibition to restricted with a loud logged
  advisory stating the plain suspension risk — the owner's informed choice,
  recorded in `audit/tos_acknowledgments.jsonl`.
- **Reddit:** automated upvoting is vote manipulation — **prohibited**. Bots
  are otherwise welcome where non-spammy and subreddit-rule-compliant.
- **YouTube:** automated outreach is spam (no creator DM feature) —
  **prohibited**; fake engagement of any kind is banned.
- **TikTok / Instagram / Facebook:** automation without the platform's
  permission is prohibited in the literal terms; this tool's posture is
  human-directed, low-volume, own-account operation with the constraint shown
  on every guarded call. Bulk/spammy automation stays refused by the tool's
  own anti-spam guards.

These summaries are not legal advice; the official documents govern, and they
change over time — each file records its last-checked date.
