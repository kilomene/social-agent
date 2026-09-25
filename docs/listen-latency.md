# Notification listener: latency honesty.

## What `social-agent listen` is

A fast-poll loop. Every `--interval` seconds (default 60) it runs one poll
tick on each enabled watcher of type `notification`, `comment`, or
`message`, then routes new events: classify comments, remember people,
draft replies into the approval queue, propose hides for toxic/spam,
log DMs and notify you.

## What it is not

It is **not true push**. Worst-case reaction time is roughly one poll
interval plus processing time (default ~60s). A comment posted one second
after a tick waits ~59s for the next tick.

## Truly instant delivery

Real push needs platform webhooks / streaming APIs where the platform
offers them:

- **YouTube**: PubSubHubbub webhook for new video/comment notifications.
- **Discord/Slack-style**: not applicable; these are not in the adapter set.
- **TikTok / Instagram / X / Facebook / Reddit**: no public webhook for
  "new comment on my post" on standard developer tiers; polling is the
  honest mechanism. Shortening `--interval` below ~30s risks looking like
  aggressive scraping — the ToS layer (`automated_data_collection`) still
  applies to every poll.

## Tuning

- Lower `--interval` (e.g. 30) for launch days; raise it (300+) for quiet
  accounts to stay well inside rate limits.
- `--once` runs a single pass: useful for cron jobs, tests, and exams.
- Watchers stay read-only; the listener only classifies, remembers, and
  proposes. Approval is always human (per `approvals.per_type`).
