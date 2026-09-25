# X — Terms of Service compliance notes for social-agent

Plain-language summary of the X rules that constrain what this tool may
automate. **The official documents govern, not this file, and this is not
legal advice.** X's terms change over time — re-check them periodically.

Last checked: 2026-09-25

## Official sources

- X Terms of Service: https://x.com/en/tos
- X Developer Policy (spam, bots, automation):
  https://github.com/xdevplatform/docs/blob/HEAD/developer-terms/policy.mdx
- X Rules: https://help.x.com/en/rulesandpolicies/xrules

## What X's terms say (automation-relevant)

1. **No scraping.** The Terms prohibit crawling or scraping the services "in
   any form, for any purpose" without X's prior written consent. Access is
   limited to published interfaces (the API).
2. **Automation only through the official X API.** The developer guidelines
   require automated accounts to use the official X API; non-API automation
   (browser scripting, scraping) is prohibited.
3. **No spam or platform manipulation.** Using the API to create spam or engage
   in any form of platform manipulation is prohibited.
4. **Write actions must follow the Automation Rules**: explicit consent before
   automated replies or DMs, honor opt-outs immediately, never bulk/aggressive
   actions, and bot accounts must clearly disclose they are bots.

## Honest gap for this tool

This tool is **browser-driven**, not API-driven — by the account owner's
explicit order it uses no APIs and no API keys on any platform. Under a
literal reading of X's terms, several of its automation categories are simply
not permitted on X (see below); X's developer guidelines designate the
official X API as their sanctioned path, which this tool does not use. The
tool states this plainly rather than pretending browser automation is
covered.

## What this tool may do on X

- Draft posts for human approval (the tool never publishes by itself).
  Human-directed posting that follows the Automation Rules is the only
  write-adjacent activity permitted here.
- Propose profile changes for explicit human approval.
- Low-volume, read-only reading of the user's own account, with an advisory
  shown on every guarded call (not affirmatively permitted by X's terms).
  Anything beyond this proceeds only under the explicit
  `tos.acknowledged_risk: [x]` opt-in — the owner's informed acceptance of
  the suspension risk, logged per action.

## What this tool must never do on X

- Automated likes, comments/replies, follows, or reposts — refused by the CLI.
- Automated DMs — refused by the CLI (explicit consent required; bulk banned).
- Browser-based scraping or data collection — refused by the CLI.

## Machine-readable rules

`tos_rules.yaml` in this directory encodes the above as
`prohibited` / `restricted` / `allowed` per action class. A `prohibited`
entry makes the CLI refuse the action (exit 2, logged to `refusals.jsonl`).
A `restricted` entry lets the action proceed but prints the constraint as an
advisory. The ToS layer runs **before** missions, autonomy, quiet hours, and
rate limits — no mission or approval can override a prohibition.

## Acknowledged risk (explicit user opt-in only)

The user may explicitly opt X into `tos.acknowledged_risk` in
`policy.yaml`:

```yaml
tos:
  acknowledged_risk: [x]
```

Effect: a `prohibited` classification for X is **downgraded to
restricted** — but ONLY with a loud, logged advisory (stderr +
`audit/tos_acknowledgments.jsonl`) stating the plain risk: X's terms
require API-only automation, and browser-driven engagement may get the
account **suspended or banned**. Without this explicit acknowledgment,
prohibitions stay fail-closed. The risk is the **user's informed
choice**; the agent records it and never proceeds silently. Removing `x`
from the list restores fail-closed behavior immediately.
