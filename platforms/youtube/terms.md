# YouTube — Terms of Service compliance notes for social-agent

Plain-language summary of the YouTube rules that constrain what this tool may
automate. **The official documents govern, not this file, and this is not
legal advice.** YouTube's terms change over time — re-check them periodically.

Last checked: 2026-09-25

## Official sources

- YouTube Terms of Service: https://www.youtube.com/t/terms?gl=DE

## What YouTube's terms say (automation-relevant)

1. **No automated access.** Accessing YouTube via automated means (robots,
   botnets, scrapers) is prohibited, except for public search engines in
   accordance with robots.txt or with prior written permission.
2. **No fake engagement.** Nothing that artificially increases views, likes,
   comments, or subscribers via automatic systems; legitimate engagement must
   reflect a human user's authentic intent.
3. **No spam.** Unsolicited promotional content and misleading metadata are
   prohibited.
4. **No harvesting** of usernames, faces, or other personal data.

## What this tool may do on YouTube

- Propose **genuine, human-directed, low-volume** engagement (likes, comments,
  subscriptions) that reflects real interest. Every one of these still
  requires the user's explicit per-action approval.
- Draft video/post metadata for human approval (the tool never publishes by
  itself). Actual uploads are performed through the persistent browser
  session in YouTube Studio with the user's logged-in account — no API keys,
  no OAuth apps; this tool uses no YouTube API services.
- Low-volume, read-only monitoring of the user's own channel activity, with
  the advisory shown on every guarded call. Automated access is restricted
  under YouTube's terms; the tool stays human-directed and low-volume.

## What this tool must never do on YouTube

- Anything that artificially inflates views, likes, comments, or subscribers.
- Automated commenting at scale, spam, or unsolicited promotional outreach
  (there is no creator DM feature; automated outreach is spam — refused).
- Scraping YouTube data or harvesting user data via automated means.

## Machine-readable rules

`tos_rules.yaml` in this directory encodes the above as
`prohibited` / `restricted` / `allowed` per action class. A `prohibited`
entry makes the CLI refuse the action (exit 2, logged to `refusals.jsonl`).
A `restricted` entry lets the action proceed but prints the constraint as an
advisory. The ToS layer runs **before** missions, autonomy, quiet hours, and
rate limits — no mission or approval can override a prohibition.
