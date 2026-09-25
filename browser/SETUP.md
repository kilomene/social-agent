# Browser engine setup

The agent drives Facebook, Instagram, X, YouTube, Reddit, and TikTok
through a **real Chromium browser** (Playwright) — no APIs, no API keys.
Each account gets a persistent profile on disk, so logins survive restarts
exactly like your own browser.

## Install

```bash
pip install playwright
playwright install chromium
```

Verify:

```bash
python3 -c "from playwright.sync_api import sync_playwright; print('ok')"
social-agent browser status   # reports engine availability
```

## How it works

- `browser login <account-label>` opens a **headed** (visible) Chromium
  window on the platform's login page. **You sign in yourself** — the
  agent never sees or stores your password. Close the window when done.
- The login persists in
  `<home>/accounts/<label>/browser-profile/`. From then on the agent
  reuses that profile (headless by default).
- 2FA / challenge walls: the agent **pauses, notifies you, and waits**.
  It never tries to bypass a challenge. Complete the verification with
  `browser login <account-label>` (headed), then the agent resumes.

## Headed vs headless

- **First login:** headed (you must see the window to sign in).
- **Daily operation:** headless (faster, no window). Use
  `browser open <account-label> --headed` if you want to watch.
- **Challenge recovery:** headed.

## Troubleshooting

- `BrowserUnavailable: Playwright is not installed` → run the install
  commands above.
- `playwright install chromium` downloads ~170MB into
  `~/.cache/ms-playwright`.
- If a platform shows a challenge on every launch, the profile may be
  flagged — sign in headed once more, complete any verification, and
  avoid rapid-fire actions (the agent's human pacing + rate limits
  already do this).
