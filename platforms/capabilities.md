# Platform capabilities matrix

Honest summary of what social-agent can do per platform. "Browser" means a real
logged-in browser session driven by the user or their agent — social-agent
itself never stores credentials and never calls private endpoints directly.

| Capability | TikTok | X | Instagram | Facebook | YouTube | Reddit |
|---|---|---|---|---|---|---|
| Read feed / timeline | browser | browser / API | browser | browser | browser / API | browser / API |
| Read profile + follower counts | browser | browser / API | browser | browser / API (Pages) | browser / API | browser / API |
| Read comments | browser | browser / API | browser | browser / API (Pages) | browser / API | browser / API |
| Read notifications | browser | browser / API | browser | browser (Page inbox via API) | browser | browser / API |
| Read DMs | browser | browser / API* | browser | browser | n/a | browser (API limited) |
| Post content | browser | browser / API | browser / API (business) | API (Pages) / browser (profiles) | browser / API (quota) | browser / API |
| Like | browser | browser / API | browser | browser | browser / API | upvote via browser / API |
| Comment / reply | browser | browser / API | browser | browser / API (Pages) | browser / API | browser / API |
| Follow / subscribe | browser | browser / API | browser | browser | browser / API | browser / API |
| Repost / retweet / share | browser (share) | browser / API | n/a (share to story via browser) | browser (share) | n/a | crosspost via browser / API |
| DM send | browser (throttled) | browser / API* | browser | browser | n/a | browser |

\* X API DM access requires appropriate tier/permissions.

## Auth notes

- **Browser session** is the default path everywhere: the user signs in with
  their own browser; social-agent never sees the password.
- **Official APIs** (X, YouTube, Reddit, Meta for business/Pages) are
  documented per adapter with links; they need the user's own OAuth app or
  tokens, created outside this repo.

## Hard limits (not worked around)

- TikTok personal accounts: no public write API.
- Instagram personal accounts: no official write API.
- Facebook personal profiles: no official posting API.
- YouTube Data API: 10,000 units/day default quota.
- Reddit free API: 60 req/min.
- X free API tier: heavily limited; check current pricing.

## Rate limits enforced by social-agent

See `policy/policy.yaml` (`rate_limits`). The CLI refuses acting operations
past the per-hour/per-day caps regardless of platform headroom.

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
  browser-driven, so automated likes, comments, follows, reposts, DMs, and
  browser-based data collection are **prohibited** on X. The sanctioned path
  for automation on X is the official API — stated plainly, not worked around.
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
