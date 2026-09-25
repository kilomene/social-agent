"""core: the agent's durable brain.

- memory.py   — permanent SQLite memory (accounts, voice, people,
                campaigns, schedule, content, performance, decisions,
                SOPs, relationship graph). Survives restarts; never chat.
- backup.py   — content-addressed snapshots ("git for the agent's life").
- recovery.py — append-only action journal + crash recovery.
- install.py  — idempotent installer (~/SocialAgent/ layout).
"""
