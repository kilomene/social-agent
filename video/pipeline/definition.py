"""Pipeline schema: typed values, node lifecycle, exceptions.

Adapted from the Toonflow core model (packages/nodeScaffold/src/values.ts):
node outputs are {dataType, value} typed values; media values are
{url (workspace-relative path), mimeType}. Unconnected inputs are the
explicit UNRESOLVED sentinel, distinct from null.
"""

from __future__ import annotations

import re

PIPELINE_VERSION = "1.0.0"

# --- node lifecycle ---------------------------------------------------------
IDLE = "idle"
RUNNING = "running"
SUCCEEDED = "succeeded"
FAILED = "failed"
STATUSES = (IDLE, RUNNING, SUCCEEDED, FAILED)

# --- typed values ------------------------------------------------------------
DATA_TYPES = ("STRING", "INT", "FLOAT", "BOOLEAN",
              "IMAGE", "MASK", "VIDEO", "AUDIO", "FILE")

MEDIA_PREFIX = {"IMAGE": "image/", "MASK": "image/",
                "VIDEO": "video/", "AUDIO": "audio/"}

# Unconnected inputs are explicitly "unresolved", distinct from null.
UNRESOLVED = {"dataType": "UNRESOLVED", "value": None}


def input_ref(node_id, output_name):
    """Declare an input wired to another node's output.

    Resolved by the runner; unresolvable refs become UNRESOLVED."""
    if not node_id or not output_name:
        raise ValueError("input_ref needs node_id and output_name")
    return {"dataType": "REF", "node": node_id, "output": output_name}


def is_input_ref(obj):
    return isinstance(obj, dict) and obj.get("dataType") == "REF"


def typed_value(data_type, value):
    """Build a typed value; raises ValueError on schema violation."""
    if data_type not in DATA_TYPES:
        raise ValueError(f"bad dataType {data_type!r}; pick {DATA_TYPES}")
    _check(data_type, value)
    return {"dataType": data_type, "value": value}


def is_typed_value(obj):
    if not isinstance(obj, dict):
        return False
    dt, v = obj.get("dataType"), obj.get("value")
    if dt == "UNRESOLVED":
        return v is None
    if dt not in DATA_TYPES:
        return False
    try:
        _check(dt, v)
    except ValueError:
        return False
    return True


def is_unresolved(obj):
    return isinstance(obj, dict) and obj.get("dataType") == "UNRESOLVED"


def _check(data_type, value):
    if data_type == "STRING":
        if not isinstance(value, str):
            raise ValueError("STRING value must be str")
    elif data_type == "BOOLEAN":
        if not isinstance(value, bool):
            raise ValueError("BOOLEAN value must be bool")
    elif data_type == "INT":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("INT value must be int")
    elif data_type == "FLOAT":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("FLOAT value must be numeric")
    elif data_type in ("IMAGE", "MASK", "VIDEO", "AUDIO", "FILE"):
        if not isinstance(value, dict):
            raise ValueError(f"{data_type} value must be a media dict")
        url = value.get("url")
        mt = value.get("mimeType")
        if not isinstance(url, str) or not url.strip():
            raise ValueError(f"{data_type} media needs a non-empty url")
        if not isinstance(mt, str) or not mt.strip():
            raise ValueError(f"{data_type} media needs a mimeType")
        if data_type == "FILE":
            if not re.match(r"^[^/\s]+/[^/\s]+$", mt):
                raise ValueError(f"FILE mimeType must be type/subtype, got {mt!r}")
        else:
            want = MEDIA_PREFIX[data_type]
            if not mt.startswith(want) or len(mt) <= len(want):
                raise ValueError(
                    f"{data_type} mimeType must start with {want!r}, got {mt!r}")


# --- exceptions --------------------------------------------------------------
class PipelineError(Exception):
    """Base pipeline error; may be retried per the node's retry budget."""


class PipelineBlockedError(PipelineError):
    """SENTINEL: a hard $0/environment block (no provider, region gate, no
    ffmpeg...). Never retried, never swallowed: it fails the node and names
    exactly what blocks progress. A failed shot regenerates alone later."""


class ProviderError(PipelineError):
    """A provider call failed; retried per node retries."""


class GateFailedError(PipelineError):
    """A QC gate (A/B/C/D) failed; the node records the verdict. Retried per
    node retries because gate failures usually carry corrective instructions."""


class CancelledError(PipelineError):
    """SENTINEL: cooperative cancellation requested. Never retried."""


# --- secret hygiene -----------------------------------------------------------
_SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password|bearer)\b\s*[:=]\s*"
               r"(?P<q>['\"]?)(?P<v>[A-Za-z0-9\-_./+]{4,})(?P=q)"),
    re.compile(r"(?i)sk-[A-Za-z0-9]{8,}"),
    re.compile(r"(?i)[?&](api[_-]?key|token)=[^&\s]+"),
]


def redact_secrets(message):
    """Redact credential-like values from error/log text."""
    text = str(message)
    for pat in _SECRET_PATTERNS:
        text = pat.sub(lambda m: m.group(0)[:0] + "[REDACTED]", text)
    return text


# --- node / episode specs -----------------------------------------------------
def make_node(node_id, node_type, params=None, inputs=None, deps=None,
              retries=2, label=""):
    """Build a node spec dict (validated, JSON-safe)."""
    if not node_id or not isinstance(node_id, str):
        raise ValueError("node_id must be a non-empty string")
    if not node_type or not isinstance(node_type, str):
        raise ValueError("node_type must be a non-empty string")
    deps = list(deps or [])
    inputs = dict(inputs or {})
    for k, v in inputs.items():
        if not (is_typed_value(v) or is_unresolved(v) or is_input_ref(v)):
            raise ValueError(f"input {k!r} is not a typed value or input ref")
    if int(retries) < 0:
        raise ValueError("retries must be >= 0")
    return {"id": node_id, "type": node_type, "label": label or node_id,
            "params": dict(params or {}), "inputs": inputs,
            "deps": deps, "retries": int(retries),
            "status": IDLE, "attempts": 0, "outputs": {},
            "error": None, "history": []}


def make_episode(episode_id, title, project_dir, nodes,
                 script_path="", shot_plan_path="", provider=""):
    """Build an episode spec dict."""
    if not episode_id or "/" in episode_id or episode_id.startswith("."):
        raise ValueError(f"bad episode_id {episode_id!r}")
    return {"id": episode_id, "title": title, "project_dir": project_dir,
            "script_path": script_path, "shot_plan_path": shot_plan_path,
            "provider": provider, "version": PIPELINE_VERSION,
            "nodes": list(nodes), "created_at": "", "status": "defined"}
