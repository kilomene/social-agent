"""Study-to-improve loop: the agent studies its own performance (pure stdlib).

`run_study(home)` analyzes watcher events, engagement actions, and the post
queue, then writes a dated entry to learning/journal.md: what worked, what
didn't, and 3 concrete adjustments. `propose_updates` writes PROPOSALS
(never auto-applied) for interest-profile and mission-pillar changes to
learning/proposals.md — the human reviews and applies them.

Experiments: track A/B variants (e.g. title A vs B) and conclude winners
from engagement deltas, all recorded in experiments.json.
"""

import json
import os
import time
from datetime import datetime, timezone

EVENTS_LOG = "events.jsonl"


def _read_events(home):
    p = os.path.join(home, EVENTS_LOG)
    if not os.path.exists(p):
        return []
    out = []
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    return out


def _read_json(home, name, default):
    p = os.path.join(home, name)
    if not os.path.exists(p):
        return default
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def _learning_dir(home):
    d = os.path.join(home, "learning")
    os.makedirs(d, exist_ok=True)
    return d


def run_study(home):
    """Analyze performance and append a journal entry. Returns the entry."""
    events = _read_events(home)
    actions = _read_json(home, "actions.json", [])
    queue = _read_json(home, "queue.json", [])

    by_kind = {}
    for e in events:
        by_kind[e.get("kind", "?")] = by_kind.get(e.get("kind", "?"), 0) + 1
    done = [a for a in actions if a["status"] == "done"]
    proposed = [a for a in actions if a["status"] == "proposed"]
    approved_posts = [q for q in queue if q["status"] == "approved"]

    worked, didnt, adjustments = [], [], []

    if by_kind:
        top = sorted(by_kind.items(), key=lambda x: -x[1])[:3]
        worked.append("Most observed signals: " +
                      ", ".join(f"{k} ({v}x)" for k, v in top))
    else:
        didnt.append("No watcher events recorded yet — start watchers to feed the loop.")

    if done:
        worked.append(f"{len(done)} engagement actions completed and logged.")
    if proposed and len(proposed) > len(done) * 2 and done:
        didnt.append(f"Approval bottleneck: {len(proposed)} proposals waiting vs "
                     f"{len(done)} completed.")
        adjustments.append("Clear the approval backlog: review `engage list --status proposed` "
                           "daily, or narrow the mission so fewer proposals need review.")
    crisis = sum(v for k, v in by_kind.items() if str(k).startswith("crisis"))
    if crisis:
        didnt.append(f"{crisis} crisis spike(s) detected.")
        adjustments.append("Address the top crisis topic directly with a response post — "
                           "silence lets it grow.")
    ideas = sum(v for k, v in by_kind.items() if "content-idea" in str(k))
    if ideas:
        worked.append(f"{ideas} audience content-ideas mined from comments.")
        adjustments.append("Turn the top repeated audience question into this week's video — "
                           "it is pre-validated demand.")
    trends = sum(v for k, v in by_kind.items() if str(k).startswith("trend"))
    if trends:
        adjustments.append(f"Ride {trends} on-mission trend(s): adapt one to your niche "
                           "within 48h while it's hot.")

    # Pad to 3 concrete adjustments with evergreen growth moves.
    evergreen = [
        "Double down on the best-performing pillar: check which post topics got the most engagement and shift the content mix toward them.",
        "Tighten hooks: rewrite the first line/2 seconds of the next 3 posts around one bold promise each.",
        "Post at the audience's peak hour: compare event timestamps to find when engagement clusters, then schedule there.",
    ]
    for e in evergreen:
        if len(adjustments) >= 3:
            break
        if e not in adjustments:
            adjustments.append(e)
    adjustments = adjustments[:3]

    if not worked:
        worked.append("Baseline established — not enough data yet for wins; keep polling.")

    entry = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "events_analyzed": len(events),
        "actions_done": len(done),
        "posts_approved": len(approved_posts),
        "worked": worked,
        "didnt_work": didnt,
        "adjustments": adjustments,
    }
    d = _learning_dir(home)
    with open(os.path.join(d, "journal.md"), "a", encoding="utf-8") as fh:
        fh.write(f"\n## Study — {entry['date']}\n\n")
        fh.write(f"Events analyzed: {entry['events_analyzed']}, "
                 f"actions done: {entry['actions_done']}, "
                 f"posts approved: {entry['posts_approved']}\n\n")
        fh.write("### What worked\n")
        for w in worked:
            fh.write(f"- {w}\n")
        fh.write("\n### What didn't\n")
        for w in didnt:
            fh.write(f"- {w}\n")
        fh.write("\n### 3 concrete adjustments\n")
        for i, a in enumerate(adjustments, 1):
            fh.write(f"{i}. {a}\n")
    return entry


# ------------------------------------------------------- experiments ---

def _experiments_path(home):
    return os.path.join(home, "experiments.json")


def _load_experiments(home):
    p = _experiments_path(home)
    if not os.path.exists(p):
        return []
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return []


def _save_experiments(home, exps):
    os.makedirs(home, exist_ok=True)
    p = _experiments_path(home)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(exps, fh, indent=2)
    os.replace(tmp, p)


def start_experiment(home, name, kind, variant_a, variant_b):
    exps = _load_experiments(home)
    if any(e["name"] == name for e in exps):
        raise ValueError(f"experiment {name!r} already exists")
    exps.append({
        "name": name, "kind": kind,
        "variant_a": variant_a, "variant_b": variant_b,
        "status": "running",
        "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "winner": None,
    })
    _save_experiments(home, exps)
    return name


def list_experiments(home):
    return _load_experiments(home)


def conclude_experiment(home, name, metric_a, metric_b):
    exps = _load_experiments(home)
    exp = next((e for e in exps if e["name"] == name), None)
    if exp is None:
        raise ValueError(f"unknown experiment {name!r}")
    if exp["status"] != "running":
        raise ValueError(f"experiment {name!r} is already {exp['status']}")
    metric_a, metric_b = float(metric_a), float(metric_b)
    if metric_a == metric_b:
        winner = "tie"
    else:
        winner = "A" if metric_a > metric_b else "B"
    exp.update({"status": "concluded", "metric_a": metric_a,
                "metric_b": metric_b, "winner": winner,
                "concluded": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    _save_experiments(home, exps)
    return exp


def propose_updates(home):
    """Write PROPOSALS for interest-profile / mission-pillar changes.

    Never auto-applied: the human reviews learning/proposals.md and applies
    what they agree with (e.g. by editing policy.yaml or the mission file).
    """
    entry = run_study(home)
    events = _read_events(home)
    topics = {}
    for e in events:
        for t in (e.get("data") or {}).get("topics", []) \
                if isinstance(e.get("data"), dict) else []:
            topics[t] = topics.get(t, 0) + 1
    proposals = []
    for t, n in sorted(topics.items(), key=lambda x: -x[1])[:5]:
        proposals.append(f"Consider adding interest topic {t!r} "
                         f"(seen in {n} events).")
    for a in entry["adjustments"]:
        proposals.append(f"Pillar shift candidate: {a}")
    d = _learning_dir(home)
    with open(os.path.join(d, "proposals.md"), "a", encoding="utf-8") as fh:
        fh.write(f"\n## Proposals — {entry['date']} (REVIEW ONLY, not applied)\n\n")
        for p in proposals:
            fh.write(f"- [ ] {p}\n")
    return proposals
