"""hands: the execution-ticket interface (brain -> hands).

The repo is the BRAIN; an external agent (e.g. Muse with its own
server-side Chromium and a live browser card the user watches) is the
HANDS. Approving a proposal issues an execution TICKET
(``hands.tickets``) — machine-readable JSON with the action, platform,
account, target, parameters, idempotency key, and the ToS / approval /
rate-limit receipts. The external agent claims the ticket, fulfills it
visibly in its own browser, and the operator confirms via the existing
engage done / approval flow. Tickets are idempotent: a ticket can never
be fulfilled twice.

``hands.backend`` defines the fulfillment interface; the only bundled
implementation is the mock backend used by tests and dry runs. Real
fulfillment happens outside this repo.
"""

from hands.tickets import (  # noqa: F401
    HOST_SESSIONS_FILE,
    STATUSES,
    TICKETS_FILE,
    TICKET_SCHEMA,
    TYPE_TO_ACTION,
    cancel,
    claim,
    fail,
    format_ticket,
    fulfill,
    get,
    issue,
    issue_from_approval,
    list_host_sessions,
    list_tickets,
    new_id,
    record_ticket_session,
    register_host_session,
)
from hands import steps as steps_mod  # noqa: F401
from hands.backend import HandsBackend, MockHandsBackend  # noqa: F401

__all__ = [
    "HOST_SESSIONS_FILE", "STATUSES", "TICKETS_FILE", "TICKET_SCHEMA",
    "TYPE_TO_ACTION", "cancel", "claim", "fail", "format_ticket",
    "fulfill", "get", "issue", "issue_from_approval", "list_host_sessions",
    "list_tickets", "new_id", "record_ticket_session",
    "register_host_session", "steps_mod", "HandsBackend", "MockHandsBackend",
]
