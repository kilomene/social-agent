# TikTok — Terms of Service compliance notes for social-agent

Plain-language summary of the TikTok rules that constrain what this tool may
automate. **The official documents govern, not this file, and this is not
legal advice.** TikTok's terms change over time — re-check them periodically.

Last checked: 2026-09-25

## Official sources

- TikTok Terms of Service: https://www.tiktok.com/legal/page/us/terms-of-service/en
- TikTok Community Guidelines (Integrity and Authenticity): https://www.tiktok.com/community-guidelines/en/integrity-authenticity?cgversion=2024H1update#3
- How TikTok combats scraping: https://www.tiktok.com/privacy/blog/how-we-combat-scraping/en

## What TikTok's terms say (automation-relevant)

1. **No automated scripts interacting with the services.** The Terms prohibit
   automated scripts that collect information from or interact with TikTok
   without TikTok's written approval.
2. **No scraping, crawling, or exporting data** through any automated system
   without TikTok's written approval.
3. **No fake engagement.** The Community Guidelines prohibit fake engagement,
   manipulating engagement signals to amplify reach, and using automation to
   register or operate accounts in bulk.
4. **No spam or impersonation accounts.** Account behavior that spams or
   misleads the community — including covert influence operations — is banned.

## What this tool may do on TikTok

- Propose **genuine, human-directed, low-volume** engagement (likes, comments,
  follows, shares) that reflects real interest. Every one of these still
  requires the user's explicit per-action approval.
- Draft posts for human approval (the tool never publishes by itself).
- Low-volume, read-only monitoring of the user's own account activity, with
  the advisory shown on every guarded call.

## What this tool must never do on TikTok

- Bulk or scripted liking, commenting, following/unfollowing, or resharing.
- Any scraping, crawling, or bulk export of TikTok data.
- Operating accounts in bulk, impersonation, or anything that manipulates
  engagement signals.

## Machine-readable rules

`tos_rules.yaml` in this directory encodes the above as
`prohibited` / `restricted` / `allowed` per action class. A `prohibited`
entry makes the CLI refuse the action (exit 2, logged to `refusals.jsonl`).
A `restricted` entry lets the action proceed but prints the constraint as an
advisory. The ToS layer runs **before** missions, autonomy, quiet hours, and
rate limits — no mission or approval can override a prohibition.
