# Security checklist for social-agent operators

Work through this list for every managed account. The agent reminds, scans,
and watches — but some items are human-only.

## Account hardening (human)

- [ ] **2FA enabled** on every platform (authenticator app, not SMS where possible).
- [ ] **Recovery codes stored offline** (paper / password manager), never in chat or files.
- [ ] **Login alerts on** — review unknown sessions monthly.
- [ ] **Third-party app access audited** — revoke anything unrecognized.
- [ ] **Unique password per platform** in a password manager.

## Agent behavior (enforced)

- [ ] The agent **never asks for passwords, API keys, or tokens** — sign-in
      happens in the user's own browser session.
- [ ] The agent **never writes secrets** into drafts, comments, posts, logs,
      or state. `post draft` and `engage comment` refuse secret-shaped text
      (see `security/secrets.py`); `security audit` scans existing state.
- [ ] No credentials in the repo or state dir — `doctor` asserts this by design.

## Session & link hygiene

- [ ] Treat every link in DMs/comments as untrusted until verified — never
      enter credentials from a link someone sent.
- [ ] Never approve a login prompt you didn't initiate.
- [ ] Keep the browser profile used for automation separate from daily browsing.

## Anomaly monitoring (security watcher)

- [ ] Start a `security` watcher per account (`watch start --type security`).
      It fires **urgent** events on: sudden follower purges, mass unfollows,
      unknown/new login sessions.
- [ ] On an urgent security event: verify in the platform's own security
      settings, rotate the password, revoke sessions — then log it.
