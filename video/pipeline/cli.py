"""CLI: define / run / status / inspect / retry / mark / providers.

Usage (from the social-agent repo root):
    python3 -m video.pipeline.cli <command> [options]

State lives in <home>/video_pipeline/ ($SOCIAL_AGENT_HOME or ~/SocialAgent).
The pipeline never drives a browser, never touches YouTube APIs, and never
auto-publishes: publishing is a post_video proposal for the owner.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from video.pipeline import definition as d  # noqa: E402
from video.pipeline import nodes as nodes_mod  # noqa: E402
from video.pipeline import providers as providers_mod  # noqa: E402
from video.pipeline import qc as qc_mod  # noqa: E402
from video.pipeline import runner as runner_mod  # noqa: E402
from video.pipeline import state as state_mod  # noqa: E402


def _home(args):
    return os.path.abspath(
        args.home or os.environ.get("SOCIAL_AGENT_HOME")
        or os.path.expanduser("~/SocialAgent"))


def _load_episode(home, episode_id):
    st = state_mod.EpisodeState(home, episode_id)
    return st, st.load()


# --- commands -------------------------------------------------------------------
def cmd_define(args):
    home = _home(args)
    shots = []
    if args.shots_json:
        with open(args.shots_json, encoding="utf-8") as fh:
            shots = json.load(fh)
        if isinstance(shots, dict):
            shots = shots.get("shots", [])
    node_list = nodes_mod.build_initial_nodes(
        script_path=args.script, shot_plan_path=args.shot_plan, shots=shots,
        provider=args.provider, episode_no=args.episode_no)
    episode = d.make_episode(
        args.episode_id, args.title, os.path.abspath(args.project_dir),
        node_list, script_path=args.script, shot_plan_path=args.shot_plan,
        provider=args.provider)
    episode["publish_state"] = "defined"
    st = state_mod.EpisodeState(home, args.episode_id)
    st.create(episode)
    print(f"defined episode {args.episode_id!r} "
          f"({len(node_list)} head nodes) in {st.dir}")


def cmd_run(args):
    home = _home(args)
    review = {}
    if args.review_json:
        with open(args.review_json, encoding="utf-8") as fh:
            review = json.load(fh)
    finish_params = {}
    if args.finish_json:
        with open(args.finish_json, encoding="utf-8") as fh:
            finish_params = json.load(fh)
    result = runner_mod.run(
        home, args.episode_id, provider=args.provider,
        episode_no=args.episode_no, review=review,
        finish_params=finish_params)
    print(json.dumps(result, indent=2))


def cmd_status(args):
    home = _home(args)
    st, doc = _load_episode(home, args.episode_id)
    summary = st.summary()
    print(json.dumps(summary, indent=2))
    if args.verbose:
        for n in doc["nodes"]:
            err = f" :: {n['error']}" if n.get("error") else ""
            print(f"  [{n['status']:^9}] {n['id']} ({n['type']})"
                  f" attempts={n['attempts']}{err}")


def cmd_inspect(args):
    home = _home(args)
    st, _ = _load_episode(home, args.episode_id)
    node = st.node(args.node)
    print(json.dumps(node, indent=2)[:6000])


def cmd_retry(args):
    home = _home(args)
    st, _ = _load_episode(home, args.episode_id)
    st.reset_node(args.node, reason=args.reason or "operator retry")
    print(f"node {args.node!r} reset to idle (outputs kept)")


def cmd_mark(args):
    """Record a host-side publish transition (upload/schedule/approve/air).

    These steps happen in the host's live browser (YouTube Studio); the
    pipeline only records the state the host reports. Transitions must
    advance one step; the machine refuses skips."""
    home = _home(args)
    st, doc = _load_episode(home, args.episode_id)
    current = doc.get("publish_state", "defined")
    new = qc_mod.advance_publish_state(current, args.to)
    doc["publish_state"] = new
    hist = doc.setdefault("publish_history", [])
    hist.append({"at": state_mod.utcnow(), "from": current, "to": new,
                 "note": args.note or ""})
    st.save()
    print(f"publish_state: {current} -> {new}")


def cmd_providers(args):
    for p in providers_mod.list_providers():
        caps = [c for c in ("generate_image", "generate_video",
                            "generate_audio", "get_price", "get_balance",
                            "process_media") if p.has(c)]
        free = "FREE" if not p.rules else "needs-config"
        print(f"{p.id:15} {p.label:42} [{free}] caps={','.join(caps)}")


def cmd_gate(args):
    """Run a single gate directly (for inspection/testing)."""
    home = _home(args)
    if args.gate == "a":
        st, doc = _load_episode(home, args.episode_id)
        inv_path = os.path.join(st.dir, "dialogue-inventory.json")
        if not os.path.exists(inv_path):
            raise SystemExit("run the parse_script node first "
                             "(no dialogue-inventory.json)")
        with open(inv_path, encoding="utf-8") as fh:
            parsed = json.load(fh)
        result = qc_mod.gate_a(doc["project_dir"], parsed,
                               episode_no=args.episode_no)
    elif args.gate == "d":
        result = {"hint": "gate_d needs a finish node; see gate-d.json"}
    else:
        raise SystemExit(f"direct gate run only supports 'a' (got {args.gate!r})")
    print(json.dumps(result, indent=2)[:6000])
    if not result["passed"]:
        raise SystemExit(1)


# --- parser -----------------------------------------------------------------------
def build_parser():
    ap = argparse.ArgumentParser(
        prog="video-pipeline",
        description="Node-based, resumable video production pipeline.")
    ap.add_argument("--home",
                    help="SOCIAL_AGENT_HOME (default: env or ~/SocialAgent)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("define", help="define an episode DAG")
    p.add_argument("--episode-id", required=True)
    p.add_argument("--title", default="")
    p.add_argument("--project-dir", required=True)
    p.add_argument("--script", default="",
                   help="screenplay markdown, relative to project dir")
    p.add_argument("--shot-plan", default="",
                   help="shot plan markdown, relative to project dir")
    p.add_argument("--shots-json", default="",
                   help="explicit shot list JSON (overrides shot plan)")
    p.add_argument("--provider", default="local-ffmpeg")
    p.add_argument("--episode-no", type=int, default=1)
    p.set_defaults(func=cmd_define)

    p = sub.add_parser("run", help="run (or resume) the episode DAG")
    p.add_argument("--episode-id", required=True)
    p.add_argument("--provider", default="")
    p.add_argument("--episode-no", type=int, default=1)
    p.add_argument("--review-json", default="",
                   help="recorded self-review evidence for GATE B")
    p.add_argument("--finish-json", default="",
                   help="finish-node params (metadata, records, paths)")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("status", help="episode + node status summary")
    p.add_argument("--episode-id", required=True)
    p.add_argument("--verbose", "-v", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("inspect", help="dump one node's record")
    p.add_argument("--episode-id", required=True)
    p.add_argument("--node", required=True)
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("retry", help="reset a node to idle (retry it)")
    p.add_argument("--episode-id", required=True)
    p.add_argument("--node", required=True)
    p.add_argument("--reason", default="")
    p.set_defaults(func=cmd_retry)

    p = sub.add_parser("mark",
                       help="record a host-side publish transition")
    p.add_argument("--episode-id", required=True)
    p.add_argument("--to", required=True,
                   choices=list(qc_mod.PUBLISH_STATES))
    p.add_argument("--note", default="")
    p.set_defaults(func=cmd_mark)

    p = sub.add_parser("providers", help="list providers + capabilities")
    p.set_defaults(func=cmd_providers)

    p = sub.add_parser("gate", help="run a single gate directly")
    p.add_argument("gate", choices=["a", "d"])
    p.add_argument("--episode-id", required=True)
    p.add_argument("--episode-no", type=int, default=1)
    p.set_defaults(func=cmd_gate)

    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
