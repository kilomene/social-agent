"""Facebook DM adapter: stub (not configured).

No Facebook account is registered in this brain yet and no live-browser
DM flow has been worked out for it. The adapter stays a stub with a clear
reason instead of half-working code. To enable: register the account,
verify the web DM flow live, then implement check_steps()/normalize()
following platforms/x.py.
"""

PLATFORM = "facebook"
STATUS = "stub"

REASON = ("facebook DM agent not configured: no account registered and no "
          "verified web DM flow. See dm_agents/README.md.")


def readiness():
    return False, REASON


def check_steps(account, threads):
    raise NotImplementedError(REASON)


def normalize(raw):
    raise NotImplementedError(REASON)
