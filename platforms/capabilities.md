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
