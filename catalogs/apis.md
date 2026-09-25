# Official APIs & MCP servers (10)

Only official developer documentation. Anything not listed here was left out
because it is unofficial, deprecated, or could not be verified.

## Official platform APIs (6)

1. **X API v2** — https://docs.x.com/x-api/introduction — posts, timelines, DMs (tiered pricing).
2. **YouTube Data API v3** — https://developers.google.com/youtube/v3 — videos, comments, channels (quota-based).
3. **Reddit API** — https://www.reddit.com/dev/api/ — posts, comments, inbox (OAuth, rate-limited).
4. **Instagram Platform (Meta)** — https://developers.facebook.com/docs/instagram-platform/ — business/creator accounts.
5. **Facebook Pages API** — https://developers.facebook.com/docs/pages-api/ — Page publishing and inbox.
6. **TikTok Login Kit + Content Posting API** — https://developers.tiktok.com/doc/login-kit-web/ — sign-in plus video upload/publish for approved developer apps (no general write API for ordinary accounts).

## MCP servers (4)

7. **Model Context Protocol servers registry** — https://github.com/modelcontextprotocol/servers — official community registry; search it for social integrations.
8. **MCP homepage** — https://modelcontextprotocol.io — what MCP is and how to build servers.
9. **MCP Inspector** — https://github.com/modelcontextprotocol/inspector — test MCP servers locally.
10. **Anthropic MCP docs** — https://docs.anthropic.com/en/docs/mcp — how agents consume MCP tools.

Honest note: there are no first-party "TikTok/Instagram MCP servers" from those
platforms at the time of writing; community servers exist but vary in quality
and safety. Prefer official APIs above, and keep the approval-gated model of
this repo for anything that acts.

Count: 10 entries (6 official APIs + 4 MCP references).

URL verification (2026-09-24): every link above was curl-checked except
developers.tiktok.com (TikTok's CDN blocks automated checks, so its Login Kit
link was verified via web search instead) and the 403/429s from bot-blocking
sites (socialbee.com, reddit.com/dev/api, vidiq.com), which are live for real
browsers.
