# Reddit — Terms of Service compliance notes for social-agent

Plain-language summary of the Reddit rules that constrain what this tool may
automate. **The official documents govern, not this file, and this is not
legal advice.** Reddit's terms change over time — re-check them periodically.

Last checked: 2026-09-25

## Official sources

- Reddit User Agreement: https://redditinc.com/policies/user-agreement-july-1-2026
- Reddit Data API Terms: https://redditinc.com/policies/data-api-terms

## What Reddit's terms say (automation-relevant)

1. **No scraping without consent.** The User Agreement prohibits accessing,
   searching, or collecting data by automated means except as permitted in the
   Terms; scraping without Reddit's prior written consent is prohibited.
   Crawling in accordance with robots.txt is conditionally permitted.
2. **Bulk access belongs on the Data API.** The Data API Terms grant a
   revocable license for programmatic access, with rate limits, a descriptive
   user agent, and restrictions on data use and retention — including a ban on
   using content to train ML/AI models without permission.
3. **No spam.** Reddit's Rules prohibit spam.
4. **No vote cheating or manipulation.** Automated voting is vote manipulation.

## Reddit and bots — the honest picture

Reddit has a long tradition of welcome, well-behaved bots (moderator helpers,
reminders, flair managers). Bots are permitted **where they are welcome**:
non-spammy, compliant with each subreddit's rules, rate-limited, and ideally
identifying themselves as bots. What is never permitted is spam, vote
manipulation, or bulk data extraction outside the sanctioned paths.

## What this tool may do on Reddit

- Propose comments and posts that are **non-spammy, subreddit-rule-compliant,
  and human-approved**. Bot-operated accounts should identify as bots.
- Subscribe to subreddits and crosspost where welcome (genuine, low-volume).
- Low-volume, read-only monitoring of the user's own account activity, with
  the advisory shown on every guarded call. This tool uses no Reddit API —
  it is browser-only by the account owner's explicit order; bulk collection
  is simply not something this tool does.

## What this tool must never do on Reddit

- Automated upvoting/downvoting — refused by the CLI (vote manipulation).
- Spam, unsolicited automated messages, or posting where bots are unwelcome.
- Scraping Reddit data without prior written consent.

## Machine-readable rules

`tos_rules.yaml` in this directory encodes the above as
`prohibited` / `restricted` / `allowed` per action class. A `prohibited`
entry makes the CLI refuse the action (exit 2, logged to `refusals.jsonl`).
A `restricted` entry lets the action proceed but prints the constraint as an
advisory. The ToS layer runs **before** missions, autonomy, quiet hours, and
rate limits — no mission or approval can override a prohibition.
