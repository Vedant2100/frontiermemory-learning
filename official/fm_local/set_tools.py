"""Helpers for one counted set. Run inside the guest. Counts and metadata only; no task, corpus or memory text.

  set_tools.py set-aside JOB   move trials with no reward to JOB.no-reward/ (kept, not deleted) and print how many
  set_tools.py summary JOB     one JSON line per trial, on stdout
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from frontier_memory.score import read_trial  # the official scorer's rule for reward, validity and pass


def trials(job: Path):
    return sorted(p for p in job.iterdir() if p.is_dir())


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


def summary(job: Path) -> None:
    for trial in trials(job):
        path = trial / "result.json"
        if not path.exists():
            print(json.dumps({"trial": trial.name, "finished": False}))
            continue
        r = json.loads(path.read_text())
        agent, run = r.get("agent_result") or {}, r.get("agent_execution") or {}
        details = trial / "verifier" / "grade_details.json"  # only tasks graded by an LLM judge write this
        judge = json.loads(details.read_text()).get("grading_run_status") if details.exists() else None
        log = trial / "agent" / "hermes.txt"  # Hermes prints this when it gives up on the model server
        gave_up = log.exists() and "didn't respond in time" in log.read_text(errors="ignore")
        print(json.dumps({**read_trial(trial), "finished": True, "judge_status": judge, "model_unavailable": gave_up, "input_tokens": agent.get("n_input_tokens"), "output_tokens": agent.get("n_output_tokens"),
                          "agent_started": run.get("started_at"), "agent_finished": run.get("finished_at")}))


if __name__ == "__main__":
    command, job = sys.argv[1], Path(sys.argv[2])
    if command == "set-aside":
        print(set_aside(job))
    elif command == "summary":
        summary(job)
    else:
        raise SystemExit(f"unknown command {command}")
