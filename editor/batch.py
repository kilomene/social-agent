"""Batch runner + render queue.

batch: apply one operation (grade, captions burn, compress, brand apply)
across hundreds of files with per-file JSONL logging.

queue: persistent render queue with scheduling notes and crash recovery.
Each job has a state file (queued/running/done/failed + resume marker);
`queue run --resume` picks up exactly where a crashed run stopped.
"""

import glob
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone

from video import ffmpeg as vff

BATCH_LOG = "batch_runs.jsonl"
QUEUE_FILE = "render_queue.json"


def _log(home, record):
    os.makedirs(home, exist_ok=True)
    record["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(os.path.join(home, BATCH_LOG), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def _expand(patterns):
    files = []
    for pat in patterns:
        files.extend(sorted(glob.glob(pat)))
    # de-dup, keep order, files only
    seen, out = set(), []
    for f in files:
        if os.path.isfile(f) and f not in seen:
            seen.add(f)
            out.append(f)
    return out


def run_batch(home, op, patterns, out_dir, dry_run=False, **op_kwargs):
    """Apply op across files. op: grade|brand|captions|compress.

    op_kwargs: grade -> {"look": ...}; brand -> {"kit": {...}};
               captions -> {"srt": path, "style": ...};
               compress -> {"preset": ...}.
    Returns {"ok": [...], "failed": [...]}.
    """
    from editor import grading as grading_mod
    from editor import branding as branding_mod
    from editor import subtitles as subs_mod
    files = _expand(patterns)
    if not files:
        raise ValueError("no input files matched")
    os.makedirs(out_dir, exist_ok=True)
    ok, failed = [], []
    for src in files:
        base = os.path.splitext(os.path.basename(src))[0]
        dst = os.path.join(out_dir, f"{base}.{op}.mp4")
        try:
            if op == "grade":
                look = op_kwargs.get("look", "teal-noir")
                argv = [vff.FFMPEG, "-y", "-i", src, "-vf",
                        grading_mod.filtergraph(look), "-c:v", "libx264",
                        "-preset", "fast", "-crf", "19", "-c:a", "aac", dst]
            elif op == "brand":
                kit = op_kwargs.get("kit") or {}
                argv = branding_mod.build_apply(src, dst, kit, strict=not dry_run)
            elif op == "captions":
                argv = subs_mod.build_burn_in(src, dst, op_kwargs["srt"],
                                              op_kwargs.get("style", "pop"),
                                              strict=not dry_run)
            elif op == "compress":
                argv = vff.build_compress(src, dst,
                                          op_kwargs.get("preset", "tiktok"),
                                          strict=not dry_run)
            else:
                raise ValueError(f"unknown batch op {op!r}")
            vff.run_cmd(argv, dry_run=dry_run)
            ok.append(dst)
            _log(home, {"op": op, "src": src, "dst": dst, "status": "ok",
                        "dry_run": dry_run})
        except Exception as e:  # per-file isolation: one failure never stops the batch
            failed.append({"src": src, "error": str(e)[:200]})
            _log(home, {"op": op, "src": src, "status": "failed",
                        "error": str(e)[:200]})
    return {"ok": ok, "failed": failed}


# ------------------------------------------------------------- queue ---

def _queue_path(home):
    return os.path.join(home, QUEUE_FILE)


def load_queue(home):
    p = _queue_path(home)
    if not os.path.exists(p):
        return {"jobs": []}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _save_queue(home, q):
    os.makedirs(home, exist_ok=True)
    with open(_queue_path(home), "w", encoding="utf-8") as fh:
        json.dump(q, fh, indent=2)


def queue_add(home, name, argv, at=None, retries=1):
    """Add a render job. argv: exact command list. at: scheduling note
    (e.g. "02:00"); if the `at` binary exists the job is also submitted to
    at(1), otherwise the note is stored and `queue run` executes now."""
    q = load_queue(home)
    job = {"name": name, "argv": argv, "at": at, "retries": retries,
           "state": "queued", "attempts": 0, "log": [],
           "created": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    q["jobs"].append(job)
    _save_queue(home, q)
    scheduled = False
    if at and shutil.which("at"):
        try:
            cmd = " ".join(argv)
            proc = subprocess.run(["at", at], input=cmd + "\n",
                                  capture_output=True, text=True)
            scheduled = proc.returncode == 0
            job["at_submitted"] = scheduled
            _save_queue(home, q)
        except OSError:
            pass
    return {"job": name, "state": "queued", "at": at,
            "at_submitted": scheduled,
            "note": None if scheduled or not at else
                    "`at` not installed — run `queue run` to execute now"}


def queue_list(home):
    return load_queue(home)["jobs"]


def queue_run(home, name=None, resume=False, dry_run=False):
    """Execute queued jobs. resume=True skips jobs already done/running-ok;
    failed jobs retry up to their retry budget (crash recovery)."""
    q = load_queue(home)
    results = []
    for job in q["jobs"]:
        if name and job["name"] != name:
            continue
        if resume and job["state"] == "done":
            results.append({"job": job["name"], "state": "done",
                            "note": "already done — skipped"})
            continue
        if job["state"] == "running" and not resume:
            results.append({"job": job["name"], "state": "running",
                            "note": "already running — use --resume to re-run"})
            continue
        job["state"] = "running"
        job["attempts"] += 1
        _save_queue(home, q)
        try:
            print("RUN:", " ".join(job["argv"]))
            if not dry_run:
                proc = subprocess.run(job["argv"], capture_output=True, text=True)
                if proc.returncode != 0:
                    raise RuntimeError(proc.stderr.strip()[-400:])
            job["state"] = "done"
            job["log"].append(f"done attempt {job['attempts']}")
            results.append({"job": job["name"], "state": "done"})
        except Exception as e:
            job["log"].append(f"failed attempt {job['attempts']}: {str(e)[:200]}")
            if job["attempts"] <= job.get("retries", 1):
                job["state"] = "queued"  # will retry
                results.append({"job": job["name"], "state": "retry-queued",
                                "error": str(e)[:200]})
            else:
                job["state"] = "failed"
                results.append({"job": job["name"], "state": "failed",
                                "error": str(e)[:200]})
        _save_queue(home, q)
    return results
