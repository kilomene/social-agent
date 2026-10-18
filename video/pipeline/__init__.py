"""Node-based, resumable video production pipeline (Toonflow core model, adapted).

Episode -> scenes -> shots as a typed DAG of nodes with persistent state,
explicit per-shot retries, QC gates (A/B/C/D), and an approvals-queue
publishing handoff. The pipeline never drives a browser, never touches
YouTube APIs, and never auto-publishes: publishing is a ``post_video``
proposal for the owner to approve, executed by the host agent in live
Chromium.

Submodules:
  definition  episode/shot/node schema, typed values, exceptions
  state       atomic persistent state + resume helpers (new dir
              <home>/video_pipeline/, never the live loop stores)
  providers   ProviderDefinition contract + importlib registry
              (see providers/ subpackage; Toonflow-derived, MIT-attributed)
  script      markdown screenplay parser (dialogue inventory, scenes)
  qc          GATE A/B/C/D checks (Workflow skills + standing orders as code)
  nodes       node executors (script_parse ... propose_publish)
  runner      topological DAG runner (statuses, retries, resume, cancel)
  cli         define/run/inspect/retry/status CLI
"""

from . import definition, state, providers, script, qc, nodes, runner, cli

__all__ = ["definition", "state", "providers", "script", "qc",
           "nodes", "runner", "cli"]

PIPELINE_VERSION = definition.PIPELINE_VERSION
