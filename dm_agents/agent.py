"""DMAgent: per-platform DM conversation agent.

One agent per (platform, account). It owns that account's DM threads
EXCLUSIVELY — the poll-based message watchers were retired from the DM
platforms so nothing double-handles a conversation.

Two beats, matching the brain/hands split:

  tick   — decide whether a check is due and, if so, issue a read-only
           ``dm_check`` execution ticket plus machine-readable hands
           instructions (threads + last_seen_ids + exact browser steps).
           The host agent reads the threads in its live Chromium.
  report — ingest the observed messages JSON the host hands back, compare
           against last_seen_id per thread (inbound only, oldest first),
           duplicate-guard, draft style-gated replies, and queue them in
           the approvals queue. Replies go out ONLY through the standard
           pipeline (ToS > crisis > approvals > rate limits > quiet
           hours); a ToS refusal surfaces as a refusal.

Cadence:
  poll_interval   default 600s, hard minimum 300s (constructor clamps).
  target_interval 35 — the owner's stated aspiration, recorded here, NOT
           enforced: each check needs a multi-minute live browser session
           on the host, so tighter loops would pile up checks faster than
           the hands can run them. The scheduled poll is the backstop.
  trigger        `tick --trigger <source>` (schedule | gmail-notification
           | manual | ...) jumps the queue: it runs immediately regardless
           of poll_interval timing. The never-pile-up rule still applies —
           a triggered tick is skipped while a check is already in flight.
           The host runtime watches platform notification emails (Gmail,
           host-side, every few minutes) and fires a triggered tick on any
           DM notification so detection lands within minutes, not cycles.

Stop conditions: explicit `stop --reason`; threads idle longer than
stop_after_idle_hours (default 48) are parked (no longer checked) until
new inbound unparks them.
"""

import json
import time

from . import get_adapter, state as state_mod
from . import replier as replier_mod

POLL_INTERVAL_DEFAULT = 600
POLL_INTERVAL_MIN = 300
# The owner's aspiration from the spec. Recorded, not enforced — see the
# module docstring for why the browser-hands floor makes it unreachable.
TARGET_INTERVAL_ASPIRATION = 35
STOP_AFTER_IDLE_HOURS_DEFAULT = 48
FIRST_RUN_LOOKBACK_S = 24 * 3600


class DMAgent:
    def __init__(self, home, platform, account, config=None, policy=None):
        cfg = dict(config or {})
        self.home = home
        self.platform = platform
        self.account = account
        self.policy = policy or {}
        interval = int(cfg.get("poll_interval", POLL_INTERVAL_DEFAULT))
        if interval < POLL_INTERVAL_MIN:
            interval = POLL_INTERVAL_MIN
        self.poll_interval = interval
        self.stop_after_idle_hours = float(
            cfg.get("stop_after_idle_hours", STOP_AFTER_IDLE_HOURS_DEFAULT))

    # ---- lifecycle ----

    def start(self):
        state_mod.set_active(self.home, self.platform, self.account,
                             True, reason="")
        state_mod.record_cycle(self.home, self.platform, self.account,
                               "agent started")
        return {"ok": True, "platform": self.platform,
                "account": self.account, "active": True}

    def stop(self, reason=""):
        state_mod.set_active(self.home, self.platform, self.account,
                             False, reason=reason or "stopped by operator")
        return {"ok": True, "platform": self.platform,
                "account": self.account, "active": False,
                "stop_reason": reason or "stopped by operator"}

    def status(self):
        st = state_mod.agent_status(self.home, self.platform, self.account)
        threads = state_mod.list_threads(self.home, self.platform,
                                         self.account)
        try:
            adapter = get_adapter(self.platform)
            ready, ready_reason = adapter.readiness()
        except KeyError as e:
            ready, ready_reason = False, str(e)
        st.update({
            "platform": self.platform,
            "account": self.account,
            "poll_interval": self.poll_interval,
            "poll_interval_min": POLL_INTERVAL_MIN,
            "target_interval_aspiration": TARGET_INTERVAL_ASPIRATION,
            "stop_after_idle_hours": self.stop_after_idle_hours,
            "adapter_ready": ready,
            "adapter_reason": ready_reason,
            "threads": [
                {"thread_id": t["thread_id"],
                 "last_seen_id": t.get("last_seen_id") or "",
                 "last_inbound_at": t.get("last_inbound_at") or 0.0,
                 "idle_parked": bool(t.get("idle_parked")),
                 "stop_reason": t.get("stop_reason") or ""}
                for t in threads
            ],
        })
        return st

    # ---- tick ----

    def _pending_ticket_open(self, ticket_id):
        """True if the pending dm_check ticket is still in flight."""
        from hands import tickets as tickets_mod
        t = tickets_mod.get(self.home, ticket_id)
        return t is not None and t.get("status") in ("issued", "claimed")

    def tick(self, trigger=None):
        """Decide whether a DM check is due; issue dm_check if so.

        Returns a dict the CLI prints (machine-readable). trigger is an
        external trigger source (schedule | gmail-notification | manual |
        ...) that jumps the poll_interval queue but never the pile-up
        guard.
        """
        adapter = get_adapter(self.platform)
        ready, ready_reason = adapter.readiness()
        if not ready:
            return {"ok": False, "refused": True, "reason": ready_reason,
                    "platform": self.platform, "account": self.account}
        st = state_mod.agent_status(self.home, self.platform, self.account)
        if not st["active"]:
            return {"ok": False, "skipped": "agent not active",
                    "reason": st["stop_reason"],
                    "platform": self.platform, "account": self.account}
        # ToS first: reading own DMs is automated_reading (restricted on
        # some platforms = low-volume own-account OK; prohibited = refuse).
        try:
            from platforms import tos as tos_mod
            tos_rule = tos_mod.check_tos(
                self.platform, "automated_reading",
                policy=self.policy or None, home=self.home)
            tos_status = (tos_rule or {}).get("status", "unknown")
        except Exception as e:  # ToSRefusal or missing rules: fail closed
            return {"ok": False, "refused": True,
                    "reason": f"ToS: {e}",
                    "platform": self.platform, "account": self.account}
        # Never pile up: skip while a previous check is still in flight.
        pending = state_mod.get_pending_check(self.home, self.platform,
                                              self.account)
        if pending:
            if self._pending_ticket_open(pending):
                return {"ok": False, "skipped": "previous check in flight",
                        "pending_ticket": pending,
                        "platform": self.platform, "account": self.account}
            state_mod.set_pending_check(self.home, self.platform,
                                        self.account, "")
        # Park threads idle past the stop window.
        now = time.time()
        parked = []
        idle_after = self.stop_after_idle_hours * 3600
        for th in state_mod.list_threads(self.home, self.platform,
                                         self.account):
            last_in = th.get("last_inbound_at") or 0.0
            if (last_in and not th.get("idle_parked")
                    and now - last_in > idle_after):
                state_mod.park_idle_thread(
                    self.home, self.platform, self.account, th["thread_id"],
                    f"idle > {self.stop_after_idle_hours}h, parked")
                parked.append(th["thread_id"])
        # Poll-interval gate. A trigger jumps this queue; nothing jumps the
        # pile-up guard above.
        last_cycle = st["last_cycle_ts"] or 0.0
        if not trigger and now - last_cycle < self.poll_interval:
            return {"ok": False, "skipped": "poll interval not elapsed",
                    "next_in_s": int(self.poll_interval - (now - last_cycle)),
                    "platform": self.platform, "account": self.account}
        threads = [
            {"thread_id": t["thread_id"],
             "last_seen_id": t.get("last_seen_id") or ""}
            for t in state_mod.list_threads(self.home, self.platform,
                                             self.account)
            if not t.get("idle_parked")
        ]
        steps = adapter.check_steps(self.account, threads)
        from hands import tickets as tickets_mod
        ticket = tickets_mod.issue(
            self.home, "dm_check", self.platform, self.account,
            target=threads[0]["thread_id"] if threads else "",
            parameters={"threads": threads,
                        "trigger": trigger or "schedule",
                        "read_only": True},
            receipts={
                "tos": {"class": "automated_reading",
                        "status": tos_status,
                        "checked": "dm-agent tick"},
                "approval": {"note": "read-only own-account DM check; "
                                     "no approval required to read"},
                "rate_limit": {"note": "read-only; no send quota consumed"},
            },
            source={"origin": "dm-agent",
                    "trigger": trigger or "schedule"})
        state_mod.set_pending_check(self.home, self.platform, self.account,
                                    ticket["id"])
        label = f"tick trigger={trigger}" if trigger else "tick schedule"
        state_mod.record_cycle(self.home, self.platform, self.account, label)
        return {
            "ok": True,
            "ticket_id": ticket["id"],
            "trigger": trigger or "schedule",
            "platform": self.platform,
            "account": self.account,
            "parked_idle_threads": parked,
            "instructions": {
                "action": "dm_check",
                "account": self.account,
                "threads": threads,
                "steps": steps,
            },
        }

    # ---- report ----

    def report(self, messages):
        """Ingest observed messages, draft replies, queue approvals.

        messages: the observed-messages JSON contract (list of threads or
        {threads: [...]}), as returned by the host's dm_check run.
        """
        adapter = get_adapter(self.platform)
        ready, ready_reason = adapter.readiness()
        if not ready:
            return {"ok": False, "refused": True, "reason": ready_reason}
        try:
            observed = adapter.normalize(messages)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        from hands import tickets as tickets_mod
        from approvals import queue as approvals_queue
        from ratelimit import controller as rl_mod

        # Fulfill the pending dm_check ticket with what was observed.
        ticket_fulfilled = None
        pending = state_mod.get_pending_check(self.home, self.platform,
                                              self.account)
        if pending:
            t = tickets_mod.get(self.home, pending)
            if t is not None and t.get("status") in ("issued", "claimed"):
                try:
                    if t["status"] == "issued":
                        # Host ran the check without a CLI claim; record it.
                        tickets_mod.claim(
                            self.home, pending, "muse", "dm-agent-report",
                            note="dm-agent report: host check completed")
                    tickets_mod.fulfill(
                        self.home, pending,
                        evidence=("dm_check observed "
                                  f"{len(observed)} message(s): "
                                  + json.dumps(messages)[:2000]),
                        note="dm-agent report")
                    ticket_fulfilled = pending
                except Exception:
                    pass
            state_mod.set_pending_check(self.home, self.platform,
                                        self.account, "")

        # Group oldest-first per thread.
        by_thread = {}
        for m in observed:
            by_thread.setdefault(m["thread_id"], []).append(m)

        summary = {"ok": True, "platform": self.platform,
                   "account": self.account,
                   "ticket_fulfilled": ticket_fulfilled,
                   "threads": []}
        now = time.time()
        for tid, msgs in sorted(by_thread.items()):
            tstate = state_mod.get_thread(self.home, self.platform,
                                          self.account, tid)
            if tstate.get("idle_parked"):
                state_mod.unpark_thread(self.home, self.platform,
                                        self.account, tid)
            last_seen = tstate.get("last_seen_id") or ""
            ids = [m["msg_id"] for m in msgs]
            if last_seen and last_seen in ids:
                new = msgs[ids.index(last_seen) + 1:]
            elif not last_seen:
                # First sight of this thread: only treat recent inbound as
                # new; older history is marked seen, not replied to.
                new = [m for m in msgs
                       if m["sender"] == "them"
                       and (not m["ts"] or now - m["ts"] < FIRST_RUN_LOOKBACK_S)]
            else:
                # Cursor not found among the observed ids (id scheme
                # changed, or a synthetic cursor was stored): fall back to
                # timestamps — only inbound newer than the last recorded
                # inbound counts as new. A message with no timestamp counts
                # only when we have never recorded inbound for this thread.
                last_in_ts = tstate.get("last_inbound_at") or 0.0
                new = [m for m in msgs
                       if m["sender"] == "them"
                       and ((m["ts"] or 0) > last_in_ts
                            or (not m["ts"] and not last_in_ts))]
            inbound_new = [m for m in new if m["sender"] == "them"]
            # Duplicate guard: skip inbound already answered in-thread
            # (a "me" message at/after it) or already queued for approval.
            me_ts = [m["ts"] for m in msgs if m["sender"] == "me"]
            pending_items = approvals_queue.list_items(self.home, "pending")
            queued_ids = { (i.get("payload") or {}).get("in_reply_to")
                           for i in pending_items
                           if i.get("type") == "dm"
                           and i.get("platform") == self.platform }
            todo = []
            for m in inbound_new:
                if m["msg_id"] in queued_ids:
                    continue
                if any(ts and m["ts"] and ts >= m["ts"] for ts in me_ts):
                    continue
                todo.append(m)
            tinfo = {"thread_id": tid, "observed": len(msgs),
                     "new_inbound": len(inbound_new),
                     "replies_queued": [], "refused": [], "rate_limited": []}
            # Oldest first, one draft each — no batching, no waiting.
            for m in todo:
                verdict = rl_mod.check(self.home, self.platform, "dm_send",
                                       self.policy or {})
                if not verdict.get("allowed"):
                    item = approvals_queue.propose(
                        self.home, "dm", self.platform, self.account,
                        summary=(f"DM reply to thread {tid} (rate-limited)"),
                        payload={"thread_id": tid,
                                 "in_reply_to": m["msg_id"],
                                 "inbound_text": m["text"][:500],
                                 "draft": "", "deferred": True},
                        reason=f"dm-agent: rate limit ({verdict.get('reason')})",
                        risk="normal", status="rate_limited",
                        retry_at=verdict.get("retry_at"))
                    tinfo["rate_limited"].append(item["id"])
                    continue
                # NOTE: no automated_dms ToS check on the DRAFT step. Drafting
                # is proposing, not sending: the prohibition's basis
                # (consent, opt-outs, bulk messaging) governs the SEND,
                # which the pipeline refuses at ticket issuance
                # (hands/tickets.issue_from_approval raises ToSRefusal for
                # dm_send on prohibited platforms). The repo proposes; it
                # never acts alone.
                draft, info = replier_mod.draft_reply(
                    self.home, self.platform, self.account, m["text"])
                item = approvals_queue.propose(
                    self.home, "dm", self.platform, self.account,
                    summary=(f"DM reply to thread {tid}: "
                             f"{info['intent']}"),
                    payload={"thread_id": tid,
                             "in_reply_to": m["msg_id"],
                             "inbound_text": m["text"][:500],
                             "draft": draft,
                             "intent": info["intent"],
                             "media_requested": info["media_requested"],
                             "fallback_used": info["fallback_used"]},
                    reason=f"dm-agent: new inbound DM ({info['detail']})",
                    risk=info["risk"])
                rl_mod.consume(self.home, self.platform, "dm_send")
                tinfo["replies_queued"].append(
                    {"approval_id": item["id"], "draft": draft,
                     "intent": info["intent"], "risk": info["risk"]})
            # Advance the cursor past everything observed — seen means seen,
            # whether or not a reply was queued.
            newest = msgs[-1]
            inbound_msgs = [m for m in msgs if m["sender"] == "them"]
            newest_in = inbound_msgs[-1] if inbound_msgs else None
            state_mod.set_last_seen(
                self.home, self.platform, self.account, tid,
                newest["msg_id"],
                last_inbound_id=newest_in["msg_id"] if newest_in else "",
                last_inbound_ts=newest_in["ts"] if newest_in else 0.0)
            summary["threads"].append(tinfo)
        state_mod.record_cycle(self.home, self.platform, self.account,
                               "report")
        return summary
