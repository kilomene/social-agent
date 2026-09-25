"""Identity/persona embodiment: on social platforms the agent IS the owner.

The agent never says "I'm an agent/AI/chatbot" in outward-facing content.
It writes in first person as the account owner, bearing the owner's name,
voice, and personality. This is the user writing as themselves through their
own agent (ghostwriter pattern) — the persona always belongs to the verified
account owner, never a third party.

`check.py` enforces this at the content gates: `post draft` and
`engage comment` run the identity check alongside the voice check. A draft
that breaks identity (claims to be an AI, disclaims opinions robotically,
violates the persona's never-say list) is REFUSED and logged to
refusals.jsonl — the same refusal pattern as the rest of the repo.
"""
