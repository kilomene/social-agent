"""DM agent platform adapters.

Each adapter module exposes:
  PLATFORM          platform name
  STATUS            "ready" | "refused" | "stub"
  readiness()       -> (ok: bool, reason: str)
  check_steps(account, threads) -> [str]
      Plain-language browser steps for the host agent (hands). Never
      selectors, never credentials.
  normalize(raw)    -> [message dict]
      Normalize observed messages into:
      {thread_id, msg_id, sender ("them"|"me"), text, ts}

The observed-messages JSON contract (what ``dm-agent report --messages``
ingests) is a list of threads:
  [{"thread_id": "...",
    "messages": [{"id": "...", "from": "them"|"me",
                  "text": "...", "ts": 1234567890.0}, ...]}, ...]
"""

SUPPORTED = ("x", "tiktok", "instagram", "facebook", "threads")
