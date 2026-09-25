# Platform capabilities matrix

Honest summary of what social-agent can do per platform. "Browser" means the
external agent's own live browser — the browser card the user watches — with
the user's own logged-in session, fulfilling approved execution tickets
(`docs/HOST_BROWSER.md`). There is no API backend: no API clients, no API
keys, no OAuth apps — this repo contains zero platform-API integrations by
the account owner's explicit order.

| Capability | TikTok | X | Instagram | Facebook | YouTube | Reddit | LinkedIn |
|---|---|---|---|---|---|---|---|
| Read feed / timeline | browser | browser | browser | browser | browser | browser | browser |
| Read profile + follower counts | browser | browser | browser | browser | browser | browser | browser |
| Read comments | browser | browser | browser | browser | browser | browser | browser |
| Read notifications | browser | browser | browser | browser | browser | browser | browser |
| Read DMs | browser | browser | browser | browser | n/a | browser | browser |
| Post content | browser | browser | browser | browser | browser | browser | browser (drafts only, human posts) |
| Like | browser | browser | browser | browser | browser | upvote: refused (vote manipulation) | react: refused (ToS) |
| Comment / reply | browser | browser | browser | browser | browser | browser | refused (ToS) |
| Follow / subscribe | browser | browser | browser | browser | browser | browser | follow/connect: refused (ToS) |
| Repost / retweet / share | browser (share) | browser | share to story via browser | browser (share) | n/a | crosspost via browser | refused (ToS) |
| DM send | browser (throttled) | browser | browser | browser | n/a | browser | refused (spam) |

## Auth notes

- **Browser session** is the only path everywhere: the host agent acts
  logged-in in its own live Chromium — the user's own session, where
  login state already exists. If sign-in is needed, it goes through the
  vault-backed browser flow with the user's approval. social-agent
  never sees passwords, tokens, or 2FA codes and never stores
  credentials.
- There is no alternative auth path. Any `backend`, `api_key`, `api_secret`,
  or OAuth config for a social platform is not supported and never was
  shipped.

## Rate limits enforced by social-agent

See `policy/policy.yaml` (`rate_limits`). The CLI refuses acting operations
past the per-hour/per-day caps regardless of platform headroom. Every
approved action is ToS-checked before a plan is minted and flows through
the central rate-limit controller — the host's live browser is the
execution surface, not a bypass, and it is not an API.

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
  through the official X API and prohibit non-API automation. Live
  execution here happens in the host agent's live Chromium by the
  owner's explicit order, so browser-based likes, comments, follows,
  reposts, DMs, and data collection are **prohibited**
  on X. They proceed only under the explicit `tos.acknowledged_risk: [x]`
  opt-in, which downgrades the prohibition to restricted with a loud logged
  advisory stating the plain suspension risk — the owner's informed choice,
  recorded in `audit/tos_acknowledgments.jsonl`.
- **Reddit:** automated upvoting is vote manipulation — **prohibited**. Bots
  are otherwise welcome where non-spammy and subreddit-rule-compliant.
- **YouTube:** automated outreach is spam (no creator DM feature) —
  **prohibited**; fake engagement of any kind is banned.
- **LinkedIn:** scraping/crawling and unauthorized automation are prohibited by the User Agreement — automated likes, comments, follows/connects, reshares, DMs, and browser-based data collection are **prohibited** (fail closed; `tos.acknowledged_risk: [linkedin]` opt-in only). Posting is drafts-for-human-approval; comment moderation on own posts is allowed.
- **TikTok / Instagram / Facebook:** automation without the platform's
  permission is prohibited in the literal terms; this tool's posture is
  human-directed, low-volume, own-account operation with the constraint shown
  on every guarded call. Bulk/spammy automation stays refused by the tool's
  own anti-spam guards.

These summaries are not legal advice; the official documents govern, and they
change over time — each file records its last-checked date.
