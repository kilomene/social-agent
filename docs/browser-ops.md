# Browser operations

How the agent's persistent browser automation works, end to end.
Companion docs: `browser/SETUP.md` (install), `policy/guardrails.md` §27
(safety rules), `platforms/browser/` (per-platform recipes).

## Persistent profile layout

```
<home>/accounts/<label>/
  browser-profile/     Chromium profile: cookies, localStorage, logins.
                       THIS is what makes the browser "persistent".
  browser.json         sidecar: platform, status (new|login_pending|
                       active|challenge), timestamps. No credentials.
```

One profile per account label. Delete `browser-profile/` to force a
fresh login (the sidecar goes back to `new`).

## What "persistent" means

Three things together survive an agent restart:

1. **The profile dir** — the browser's own storage. Logins persist
   exactly like your personal browser.
2. **The journal** (`audit/journal.jsonl`) — every browser primitive is
   logged BEFORE it executes with an idempotency key, marked
   completed/failed after. A crash mid-action replays safely:
   `recover` verifies against real state and never repeats a completed
   post/like/comment.
3. **The sidecar** (`browser.json`) — tells the agent whether the
   profile is fresh, active, or paused on a challenge.

## First-login procedure

```bash
social-agent browser login --account main --platform x
```

1. A **headed** Chromium window opens on the platform's login page.
2. **You sign in yourself** — username, password, any 2FA, all in the
   window. The agent cannot see your screen or your password.
3. Accept "remember me" / "save login info" prompts so the session sticks.
4. Close the window. The profile now holds the login.

After that, agent-driven work reuses the profile headlessly:

```bash
social-agent browser act --account main --platform x --action like \
  --target https://x.com/some/status/123 --simulate   # offline dry run
```

Drop `--simulate` for the real browser (requires Playwright).

## 2FA / challenge flow

If a challenge appears mid-session (checkpoint, "verify it's you",
2-step code):

1. The agent **stops immediately** — it never attempts to bypass,
   guess codes, or click through.
2. It writes a `browser_challenge` user notification (and prints it).
3. The sidecar status becomes `challenge`; further agent sessions for
   that account refuse to open until it's cleared.
4. **You** run `social-agent browser login --account main --platform x`
   (headed), complete the verification, close the window.
5. The agent resumes on the next run.

## Headed vs headless guidance

| Situation | Mode |
|---|---|
| First login | headed (you must see it) |
| Challenge recovery | headed |
| Daily agent operation | headless (default) |
| Watching/debugging | `browser open --headed` |

## Selector maintenance

Platform DOMs change without notice — selectors are the #1 failure
mode. Discipline:

- Each recipe in `platforms/browser/` carries `LAST_VERIFIED`.
- Prefer `data-testid` / `data-e2e` / `aria-label` selectors over deep
  class chains (they rot slower).
- When an action starts failing: re-verify selectors against the live
  site FIRST, in a headed session, before assuming anything else broke.
- Update `LAST_VERIFIED` when you confirm a recipe still works.

## Safety notes

- ToS is checked before every browser action (`platforms/tos.py`).
  Prohibited stays fail-closed unless the platform is explicitly listed
  in `tos.acknowledged_risk` (loud logged advisory; see guardrails §27).
- Every action passes the central rate-limit controller and the
  human-pacing layer (randomized delays, scroll-before-click,
  active hours in `policy.yaml → browser.active_hours`).
- Evidence screenshots land in `audit/evidence/` for acting primitives.
