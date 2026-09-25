# Facebook — Terms of Service compliance notes for social-agent

Plain-language summary of the Facebook/Meta rules that constrain what this
tool may automate. **The official documents govern, not this file, and this
is not legal advice.** Meta's terms change over time — re-check them
periodically.

Last checked: 2026-09-25

## Official sources

- Facebook Terms of Service: https://www.facebook.com/terms.php
- Meta developer docs — automated data collection:
  https://developers.facebook.com/docs/development/terms-and-policies/automated-data-collection/?locale=en_US

## What Facebook's terms say (automation-relevant)

1. **No automated data access without permission.** Terms section 3.2.3: you
   may not access or collect data from Meta's products using automated means
   without prior permission — even while logged in.
2. **Platform APIs are the only allowable programmatic access.** Meta's
   developer docs state that other tools or techniques for automated data
   collection violate the Terms.
3. **No misleading, fraudulent, or unlawful behavior**, and no infringing
   others' rights.

## What this tool may do on Facebook

- Propose **genuine, human-directed, low-volume** engagement (likes, comments,
  follows, shares) that reflects real interest. Every one of these still
  requires the user's explicit per-action approval.
- Draft posts for human approval (the tool never publishes by itself).
- Low-volume, read-only monitoring of the user's own account activity, with
  the advisory shown on every guarded call. Note this is not affirmatively
  permitted by Meta's terms. This tool never uses Meta's APIs — by the
  account owner's explicit order it is browser-only; Meta's terms treat
  automated collection as requiring prior permission, and the
  `tos.acknowledged_risk` opt-in records the owner's informed acceptance
  of the suspension risk.

## What this tool must never do on Facebook

- Bulk or scripted liking, commenting, following/unfollowing, or sharing.
- Automated collection or export of Facebook data without permission.
- Accessing data the user has no permission to access.

## Machine-readable rules

`tos_rules.yaml` in this directory encodes the above as
`prohibited` / `restricted` / `allowed` per action class. A `prohibited`
entry makes the CLI refuse the action (exit 2, logged to `refusals.jsonl`).
A `restricted` entry lets the action proceed but prints the constraint as an
advisory. The ToS layer runs **before** missions, autonomy, quiet hours, and
rate limits — no mission or approval can override a prohibition.
