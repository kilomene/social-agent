# Threads — Terms of Service compliance notes for social-agent

Plain-language summary of the Threads rules that constrain what this tool
may automate. **The official documents govern, not this file, and this is not
legal advice.** Threads' terms change over time — re-check them
periodically.

Last checked: 2026-09-25

## Official sources

- Threads Terms of Use: https://help.instagram.com/769983657850450
- Threads API documentation (Meta's sanctioned automation path):
  https://developers.facebook.com/docs/threads

Threads is a Meta product and Threads accounts are tied to Instagram; the
Meta Terms of Service apply alongside the Threads Terms of Use.

## What Threads' terms say (automation-relevant)

1. **No automated access or collection without express permission.** You may
   not access the service or collect information in automated ways without
   Meta's express permission — even while logged in.
2. **No inauthentic engagement.** Misleading, fraudulent, or inauthentic
   behavior is prohibited.
3. **Meta's sanctioned automation path is its official developer interface,**
   not browser automation. Browser-based automation is not affirmatively
   permitted.

## What this tool may do on Threads

- Propose **genuine, human-directed, low-volume** engagement (likes, replies,
  reposts, quotes, follows) that reflects real interest. Every one of these
  still requires the user's explicit per-action approval.
- Draft posts for human approval (the tool never publishes by itself).
- Low-volume, read-only monitoring of the user's own account activity, with
  the advisory shown on every guarded call. Note this is not affirmatively
  permitted by the Terms — keep it minimal.

## What this tool must never do on Threads

- Bulk or scripted liking, replying, reposting, quoting, or
  following/unfollowing.
- Automated collection or export of Threads data without permission.
- Creating accounts automatically, or buying/selling accounts or data.

## Machine-readable rules

`tos_rules.yaml` in this directory encodes the above as
`prohibited` / `restricted` / `allowed` per action class. A `prohibited`
entry makes the CLI refuse the action (exit 2, logged to `refusals.jsonl`).
A `restricted` entry lets the action proceed but prints the constraint as an
advisory. The ToS layer runs **before** missions, autonomy, quiet hours, and
rate limits — no mission or approval can override a prohibition.
