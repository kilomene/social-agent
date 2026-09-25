"""Secret detection (pure stdlib).

`contains_secret(text)` -> (bool, pattern_name). Used to REFUSE drafts and
comments that contain password-like tokens, API keys, or private keys before
they are ever stored or posted. Fail-closed: anything matching a known
secret shape is treated as a secret.
"""

import re

PATTERNS = [
    ("openai_key", r"sk-[A-Za-z0-9]{20,}"),
    ("github_token", r"gh[pousr]_[A-Za-z0-9]{20,}"),
    ("aws_access_key", r"AKIA[0-9A-Z]{16}"),
    ("aws_secret", r"(?i)aws_secret[_-]?access[_-]?key['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{20,}"),
    ("slack_token", r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    ("private_key", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    ("password_assignment", r"(?i)\bpassword\s*[:=]\s*\S+"),
    ("api_key_assignment", r"(?i)\bapi[_-]?key\s*[:=]\s*['\"]?\S{12,}"),
    ("token_assignment", r"(?i)\b(token|secret)\s*[:=]\s*['\"]?\S{16,}"),
    ("bearer_token", r"(?i)bearer\s+[A-Za-z0-9\-._~+/]{20,}"),
    ("generic_long_token", r"(?i)\b(?:secret|passwd|pwd)\b.{0,20}['\"][A-Za-z0-9\-_+/=]{24,}['\"]"),
]

_COMPILED = [(name, re.compile(pat)) for name, pat in PATTERNS]


def contains_secret(text):
    """Return (True, pattern_name) if text looks like it contains a secret."""
    for name, rx in _COMPILED:
        if rx.search(text or ""):
            return True, name
    return False, ""
