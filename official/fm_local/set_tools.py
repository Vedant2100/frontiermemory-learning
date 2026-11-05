"""Helpers for one counted set. Run inside the guest. Counts and metadata only; no task, corpus or memory text.

  set_tools.py set-aside JOB   move trials with no reward to JOB.no-reward/ (kept, not deleted) and print how many
  set_tools.py summary JOB [HARNESS]     one JSON line per trial, on stdout
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from frontier_memory.score import read_trial  # the official scorer's rule for reward, validity and pass

# Hermes uses the official main-study signal. The other adapters have distinct agent artifacts,
# so their bounded scan uses the expanded provider/transport markers.
HERMES_HARNESSES = {"hermes", "exposure-none", "exposure-all", "delivery-cue", "delivery-scoped", "delivery-categorized"}
HERMES_UNAVAILABLE = ("didn't respond in time", "provider has been unresponsive")
OTHER_UNAVAILABLE = (*HERMES_UNAVAILABLE, "connection refused", "could not connect", "model_unavailable",
                     "econnrefused", "socket hang up", "upstream unreachable")


def trials(job: Path):
    return sorted(p for p in job.iterdir() if p.is_dir())


def model_unavailable(trial: Path, harness: str) -> bool | None:
    """Scan bounded agent artifacts; unknown fails closed in the host-side set validator."""
    agent_dir = trial / "agent"
    if not agent_dir.is_dir():
        return None
    files = ([agent_dir / "hermes.txt"] if harness in HERMES_HARNESSES else list(agent_dir.rglob("*")))
    files = [p for p in files if p.is_file() and p.stat().st_size <= 8 * 1024 * 1024]
    if not any(p.suffix.casefold() in {".txt", ".log", ".jsonl"} for p in files):
        return None
    markers = HERMES_UNAVAILABLE if harness in HERMES_HARNESSES else OTHER_UNAVAILABLE
    for path in files:
        try:
            text = path.read_text(errors="ignore").casefold()
        except OSError:
            continue
        if any(marker in text for marker in markers):
            return True
    return False


def set_aside(job: Path) -> int:
    """Official rule: trials with no reward are infrastructure failures, rerun and not counted."""
    moved = 0
    keep = job.parent / f"{job.name}.no-reward"
    for trial in trials(job):
        if (trial / "result.json").exists() and not read_trial(trial)["valid"]:
            keep.mkdir(exist_ok=True)
            shutil.move(str(trial), str(keep / trial.name))
            moved += 1
    return moved


def summary(job: Path, harness: str) -> None:
    for trial in trials(job):
        path = trial / "result.json"
        if not path.exists():
            print(json.dumps({"trial": trial.name, "finished": False}))
            continue
        r = json.loads(path.read_text())
        agent, run = r.get("agent_result") or {}, r.get("agent_execution") or {}
        details = trial / "verifier" / "grade_details.json"  # only tasks graded by an LLM judge write this
        judge = json.loads(details.read_text()).get("grading_run_status") if details.exists() else None
        unavailable = model_unavailable(trial, harness)
        print(json.dumps({**read_trial(trial), "finished": True, "judge_status": judge, "model_unavailable": unavailable, "input_tokens": agent.get("n_input_tokens"), "output_tokens": agent.get("n_output_tokens"),
                          "agent_started": run.get("started_at"), "agent_finished": run.get("finished_at")}))


if __name__ == "__main__":
    command, job = sys.argv[1], Path(sys.argv[2])
    if command == "set-aside":
        print(set_aside(job))
    elif command == "summary":
        if len(sys.argv) not in (3, 4):
            raise SystemExit("usage: set_tools.py summary JOB [HARNESS]")
        summary(job, sys.argv[3] if len(sys.argv) == 4 else "hermes")
    else:
        raise SystemExit(f"unknown command {command}")
