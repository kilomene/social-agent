"""Heartbeat client for social-agent (stdlib only, protocol-compatible).

Implements the same ping protocol as the heartbeat repo's CLI
(~/workspace/heartbeat-repo/bin/heartbeat):

  * ping <url>                  — one heartbeat ping (HTTP GET)
  * watch: <base>/<name>/start  — before the run
           <base>/<name>        — on success
           <base>/<name>/fail   — on failure

Every watcher run emits <base>/<watcher-id>/start then success or /fail;
the supervisor daemon emits its own heartbeat every interval (default 10s).

No dependency on the heartbeat repo's code — only the wire protocol is
shared, so either side can be swapped for any monitor that speaks it
(healthchecks.io-style ping URLs, Uptime Kuma, the heartbeat repo's daemon).

Config: heartbeat.yaml (repo root, overridable via SOCIAL_AGENT_HEARTBEAT).
When base_url is empty the client runs in log-only mode: pings are recorded
to $SOCIAL_AGENT_HOME/heartbeat.json without any network traffic.
"""

from .pinger import (
    HeartbeatConfig,
    load_config,
    ping,
    ping_path,
    watch_run,
    record_local,
    recent_pings,
)

__all__ = [
    "HeartbeatConfig",
    "load_config",
    "ping",
    "ping_path",
    "watch_run",
    "record_local",
    "recent_pings",
]
