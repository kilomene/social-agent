"""Anti-regression tripwire: the repo is browser-only for social platforms.

Per the account owner's explicit order, no social platform (TikTok, X,
Instagram, Facebook, YouTube, Reddit) may be driven through an API. There
are no API clients, no API keys, no OAuth flows, and no `backend` config
switch anywhere in the shipped code. This test scans the repo tree and
FAILS if any API surface reappears.

Deliberate exclusions (documented, not loopholes):
- `security/secrets.py` — the secret-leak *detector*; it must name secrets
  to detect them. Defensive only.
- `tests/` and `exams/` — fixtures use fake `api_key=...` values to test
  that the leak detector fires.
- `security/checklist.md` — states the agent "never asks for passwords,
  API keys, or tokens" (a prohibition, not an integration).
- `platforms/<name>/terms.md` + `tos_rules.yaml` — factual ToS
  *documentation* of what each platform's own rules say (the ToS layer
  must know the rules to enforce them). They never present an API as an
  option the agent can take.
"""

import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CRED_PAT = re.compile(r"api[_-]?key|api[_-]?secret|client[_-]?secret", re.I)
API_BACKEND_PAT = re.compile(
    r"""backend\s*:\s*["']?api["']?|          # backend: api  (yaml)
        "backend"\s*:\s*"api"|                 # "backend": "api" (json)
        ['"]backend['"]\s*,\s*['"]api['"]     # backend_for-style args
    """, re.I | re.X)
API_DOC_PAT = re.compile(
    r"docs\.x\.com/x-api|developers\.facebook\.com|"
    r"developers\.google\.com/youtube|reddit\.com/dev/api|"
    r"developers\.tiktok\.com", re.I)
OAUTH_PAT = re.compile(r"\boauth\b", re.I)

# source areas that must never mention API credentials or OAuth flows
CODE_DIRS = ["platforms", "browser", "core", "policy", "bin", "catalogs"]

# files allowed to name secrets (leak detector) or prohibit them
ALLOWLIST = {
    "security/secrets.py",
    "security/checklist.md",
}


# Files that are pure ToS *documentation* (what each platform's own rules
# say) — excluded from the doc-link/credential scans. The ToS layer must
# know the rules to enforce them; these files never offer an API the
# agent can take.
TOS_DOCS = {"terms.md", "tos_rules.yaml"}

# Markdown prose states policy ("no API keys") rather than configuring
# anything, so credential/OAuth scans apply to code + config only.
CODE_EXTS = (".py", ".yaml", ".yml", ".json", ".sh")


def _iter_source():
    for d in CODE_DIRS:
        root = os.path.join(REPO, d)
        for dp, dn, fn in os.walk(root):
            dn[:] = [x for x in dn if x != "__pycache__"]
            for f in fn:
                if f in TOS_DOCS:
                    continue
                if f.endswith((".pyc",)):
                    continue
                yield os.path.join(dp, f)


def _iter_code_config():
    return (p for p in _iter_source()
            if p.endswith(CODE_EXTS))


def _read(p):
    try:
        with open(p, encoding="utf-8", errors="strict") as fh:
            return fh.read()
    except (UnicodeDecodeError, OSError):
        return ""


def test_no_backend_selector():
    """No backend_for() and no `backend:` switch in shipped code."""
    hits = []
    for p in _iter_source():
        t = _read(p)
        if "backend_for" in t:
            hits.append(p)
    assert not hits, f"backend selector reappeared in: {hits}"


def test_no_api_backend_option():
    """No `backend: api` style setting anywhere in shipped code/config."""
    hits = []
    for p in _iter_source():
        if API_BACKEND_PAT.search(_read(p)):
            hits.append(p)
    assert not hits, f"api backend option found in: {hits}"


def test_no_api_credentials_in_source():
    """No api_key / api_secret / client_secret in shipped code + config."""
    hits = []
    for p in _iter_code_config():
        rel = os.path.relpath(p, REPO)
        if rel in ALLOWLIST:
            continue
        if CRED_PAT.search(_read(p)):
            hits.append(rel)
    assert not hits, f"API credential config found in: {hits}"


def test_no_oauth_in_source():
    """No OAuth flows for social platforms in shipped code + config."""
    hits = []
    for p in _iter_code_config():
        rel = os.path.relpath(p, REPO)
        if rel in ALLOWLIST:
            continue
        if OAUTH_PAT.search(_read(p)):
            hits.append(rel)
    assert not hits, f"OAuth reference found in: {hits}"


def test_no_platform_api_doc_links():
    """Platform specs must not link API developer docs as an option."""
    hits = []
    for p in _iter_source():
        if API_DOC_PAT.search(_read(p)):
            hits.append(os.path.relpath(p, REPO))
    assert not hits, f"platform API doc link found in: {hits}"


def test_adapter_specs_are_browser_only():
    """Every platform AdapterSpec is browser-only.

    `auth`, `readable`, `postable`, `rate_note`, and `docs` must never
    mention API — those fields describe what the agent can do / where it
    points. `not_possible` (the honest-gaps field) may quote a platform's
    ToS position (e.g. X's API-only rule) to explain *why* something is
    blocked, but it must not offer an API as an option either.
    """
    from platforms.base import SUPPORTED_PLATFORMS, get_adapter
    option_pat = re.compile(r"via API|or API|API \(|API key|API v\d|"
                            r"Content Posting API|Graph API|Data API|"
                            r"use the .*API|on the .*API\b", re.I)
    for name in SUPPORTED_PLATFORMS:
        spec = get_adapter(name)
        capability_blob = "\n".join([
            spec.auth,
            *spec.readable,
            *spec.postable,
            spec.rate_note,
            *spec.docs,
        ])
        assert not re.search(r"\bAPI\b", capability_blob), (
            f"platform spec {name!r} capability fields mention API:\n"
            f"{capability_blob}")
        gaps_blob = "\n".join(spec.not_possible)
        assert not option_pat.search(gaps_blob), (
            f"platform spec {name!r} not_possible offers an API option:\n"
            f"{gaps_blob}")
        assert "browser" in spec.auth.lower(), (
            f"platform spec {name!r} auth is not browser-based")
