# LinkedIn — Terms of Service compliance notes for social-agent

Plain-language summary of the LinkedIn rules that constrain what this tool
may automate. **The official documents govern, not this file, and this is
not legal advice.** LinkedIn's terms change over time — re-check them
periodically.

Last checked: 2026-09-25

## Official sources

- LinkedIn User Agreement: https://www.linkedin.com/legal/user-agreement
- LinkedIn Professional Community Policies:
  https://www.linkedin.com/legal/professional-community-policies

## What LinkedIn's terms say (automation-relevant)

1. **No scraping or crawling.** The User Agreement prohibits using bots,
   crawlers, browser plug-ins/add-ons, or any other unauthorized automated
   means to access the services or collect data.
2. **No unauthorized automation.** Automated likes, comments, follows,
   connection requests, messages, and reshares at scale are prohibited;
   LinkedIn enforces weekly invitation limits and behavioral throttles.
3. **No spam.** Bulk messaging, irrelevant connection blasts, and
   misleading engagement violate the Professional Community Policies.
4. **Accounts are for real people/companies.** Misrepresentation and fake
   engagement are prohibited.

## Honest gap for this tool

This tool is **browser-driven**, not API-driven — by the account owner's
explicit order it uses no APIs and no API keys on any platform. Under a
literal reading of LinkedIn's User Agreement, browser-based data
collection and automated engagement are simply not permitted (see below).
The tool states this plainly rather than pretending browser automation is
covered.

## What this tool may do on LinkedIn

- Draft posts for human approval (the tool never publishes by itself).
  Human-directed posting that follows the Professional Community Policies
  is the only write-adjacent activity permitted here.
- Propose profile changes for explicit human approval.
- Low-volume, read-only reading of the user's own account and network,
  with an advisory shown on every guarded call (not affirmatively
  permitted by LinkedIn's terms). Anything beyond this proceeds only
  under the explicit `tos.acknowledged_risk: [linkedin]` opt-in — the
  owner's informed acceptance of the restriction risk, logged per action.
- Moderate comments on the user's OWN posts (hide proposals require
  explicit approval or a pre-approved policy rule).

## What this tool refuses on LinkedIn

- Automated likes, comments, follows/connects, reshares, DMs (prohibited —
  fail closed).
- Browser-driven data collection / scraping (prohibited — fail closed).
- Bulk messaging or connection blasts (spam — out of scope).
