"""DM agents: per-platform conversational agents that own DMs exclusively.

Watchers are poll-based monitors that propose actions; they never hold a
conversation. DM agents are different: each one watches the DM threads of
one platform account and drafts a fast reply the moment the other person
writes. DM ownership lives here and ONLY here — the per-platform
``message`` watchers were retired from x/tiktok/instagram/facebook so the
two systems can never double-handle the same conversation.

Architecture (same as the rest of social-agent): the brain never drives a
browser and uses no platform APIs. A DM agent's ``tick`` issues a
read-only ``dm_check`` execution ticket (or prints machine-readable hands
instructions); the host agent (Muse, live Chromium) reads the threads and
hands the observed messages back via ``dm-agent report --messages``. The
agent compares against ``last_seen_id`` per thread, drafts a style-gated
reply, and queues it in the approvals queue. Replies go out only through
the standard pipeline (ToS > crisis > approvals > rate limits >
quiet hours) — a ToS refusal surfaces as a refusal, never a bypass.
"""

# platform -> adapter module path (lazy import keeps the CLI light)
PLATFORMS = {
    "x": "dm_agents.platforms.x",
    "tiktok": "dm_agents.platforms.tiktok",
    "instagram": "dm_agents.platforms.instagram",
    "facebook": "dm_agents.platforms.facebook",
    "threads": "dm_agents.platforms.threads",
}

SUPPORTED = tuple(PLATFORMS)


def get_adapter(platform):
    """Return the adapter module for a platform. Raises KeyError."""
    if platform not in PLATFORMS:
        raise KeyError(f"no DM agent for platform {platform!r} "
                       f"(supported: {', '.join(SUPPORTED)})")
    import importlib
    return importlib.import_module(PLATFORMS[platform])
