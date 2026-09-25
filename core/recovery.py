"""Back-compat shim: the crash-recovery implementation moved to
``core.resume_engine`` (one package per shared-core service).

``from core import recovery`` keeps working; new code should import
``core.resume_engine`` directly.
"""

from core.resume_engine import (  # noqa: F401
    begin,
    clear_runner,
    end,
    format_full_resume,
    format_report,
    full_resume,
    idempotency_key,
    mark_runner,
    recover,
    resume_watchers,
    stale_runner,
    unfinished,
    utcnow,
    verify,
)

__all__ = [
    "begin", "clear_runner", "end", "format_full_resume", "format_report",
    "full_resume", "idempotency_key", "mark_runner", "recover",
    "resume_watchers", "stale_runner", "unfinished", "utcnow", "verify",
]
