"""Fulfillment interface for execution tickets.

The repo never drives a browser. A HandsBackend represents the EXTERNAL
agent — e.g. Muse with its own server-side Chromium and a live browser
card the user watches — that claims execution tickets and fulfills them
visibly.

The interface is intentionally tiny: ``claim`` / ``fulfill`` live in
``hands.tickets`` (journaled, idempotent); the backend's job is just to
perform the ticket's steps in a real browser and return evidence text.

The only bundled implementation is MockHandsBackend (tests/dry runs).
Real fulfillment happens outside this repo.
"""


class HandsBackend:
    """External agent that fulfills execution tickets in its own browser."""

    name = "base"

    def fulfill(self, ticket):
        """Perform the ticket's steps and return evidence text.

        Must raise on failure (the caller marks the ticket failed).
        """
        raise NotImplementedError


class MockHandsBackend(HandsBackend):
    """Simulated external agent for tests and dry runs.

    Records every ticket it "fulfills" and returns canned evidence.
    Never touches a browser, a network, or any credential.
    """

    name = "mock"

    def __init__(self):
        self.fulfilled = []  # ticket ids, in order

    def fulfill(self, ticket):
        evidence = (
            f"[mock-hands] {ticket['action']} on "
            f"{ticket['platform']}/{ticket['account']}"
            + (f" target={ticket['target']}" if ticket.get("target") else "")
            + " — performed visibly in the mock browser card"
        )
        self.fulfilled.append(ticket["id"])
        return evidence
