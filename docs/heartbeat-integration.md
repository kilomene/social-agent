# Heartbeat integration

Every component of social-agent has its own heartbeat, speaking the same
ping protocol as the heartbeat repo's CLI
(`~/workspace/heartbeat-repo/bin/heartbeat`):

```
ping <base>/<name>/start   # a run begins
ping <base>/<name>         # it succeeded
ping <base>/<name>/fail    # it failed
```

The `heartbeat/` package in this repo implements that protocol in pure
stdlib Python (`heartbeat/pinger.py`) — no dependency on the heartbeat
repo's code, so either side can be replaced by any monitor that speaks the
same URL pattern (healthchecks.io-style push URLs, Uptime Kuma, etc.).

## What emits heartbeats

| Component | Heartbeat name | When |
|---|---|---|
| `watch run <id>` | `<watcher-id>` | `/start` before each poll, then success or `/fail` |
| `heartbeat daemon` (supervisor) | `social-agent-supervisor` (configurable) | every tick (default 10s) |
| `heartbeat test` | `heartbeat-test` | on demand |

Per-watcher overrides live in `heartbeat.yaml`:

```yaml
watchers:
  w-abc123:
    enabled: false            # no heartbeats for this watcher
    url: https://push.example.com/xyz   # watcher-specific monitor URL
```

## Modes

- **Log-only mode** (default, `base_url: ""`): no network traffic. Every ping
  is still recorded to `$SOCIAL_AGENT_HOME/heartbeat.json` with a timestamp,
  so exams and audits work offline.
- **Monitored mode** (`base_url: https://...`): pings are HTTP GETs against
  your monitor, exactly like `heartbeat ping <url>`.

## Pairing with the heartbeat repo

The heartbeat repo adds the operational layer social-agent deliberately
doesn't duplicate:

1. **Monitored cron jobs** — wrap any social-agent command:
   `heartbeat watch https://monitor.example.com/social -- social-agent watch run w-abc123`
   pings `/start`, then success or `/fail` around the command.
2. **Forever daemon** — `heartbeat daemon --url <url>` pings every 10s from
   outside the process, so a hung supervisor is itself detected.
3. **Crontab validation** — `heartbeat check` validates watcher cron schedules.
4. **Scaffolding** — `heartbeat scaffold` generates a monitored-cron project
   you can drop social-agent commands into.

Typical production shape:

```
cron: */5 * * * * heartbeat watch <base>/poll -- social-agent heartbeat daemon --once --watchers w-1,w-2
                                        ^--- heartbeat repo          ^--- this repo (supervisor tick)
```

The outer `heartbeat watch` catches "the daemon never ran"; the inner
per-watcher pings catch "watcher X's poll failed". Both speak the same
protocol, so one monitoring dashboard covers both repos.

## Commands

- `social-agent heartbeat status` — config + recent ping log.
- `social-agent heartbeat test` — test-ping the configured base URL
  (or report log-only mode).
- `social-agent heartbeat daemon [--interval N] [--once] [--watchers w1,w2]` —
  supervisor loop: supervisor heartbeat + one poll tick for each due watcher.
