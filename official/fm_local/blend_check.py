"""Check that every finished trial of the blend arm really received its rewritten task description (B6).

For each trial: agent/arm-report.json says arm blend, and the first user message of the saved Hermes session
(agent/hermes-session.jsonl) hashes to the report's blend hash, which in turn matches the map entry for that task (and a
trial the map marked as failed ran the original). Prints counts and pass/fail only. Guest system Python, standard library.

    python3 blend_check.py <task job dir> <blend-instructions.json>
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blend_logic as B  # noqa: E402


def first_user_message(session: Path) -> str | None:
    for line in session.read_text().splitlines():
        for m in json.loads(line).get("messages") or []:
            if m.get("role") == "user":
                c = m.get("content")
                return c if isinstance(c, str) else json.dumps(c)
    return None


def check_trial(trial: Path, bmap: dict) -> list[str]:
    result = json.loads((trial / "result.json").read_text())
    task = (result.get("task_name") or trial.name.split("__")[0]).split("/")[-1]
    report_path = trial / "agent" / "arm-report.json"
    if not report_path.is_file():
        return ["no arm report"]
    report = json.loads(report_path.read_text())
    entry = bmap.get(task)
    bad = []
    if report.get("arm") != "blend":
        bad.append("not the blend arm")
    if entry is None:
        return bad + [f"task {task!r} not in the map"]
    want = entry.get("blend_sha") if entry.get("ok") else entry["orig_sha"]
    if report.get("blend_sha256") != want:
        bad.append("report hash differs from the map")
    session = trial / "agent" / "hermes-session.jsonl"
    msg = first_user_message(session) if session.is_file() else None
    if msg is None:
        bad.append("no saved user message")
    elif B.sha(msg) != want:
        bad.append("the model's first message is not the expected task text")
    return bad


def main(argv: list[str]) -> int:
    job, bmap = Path(argv[1]), json.loads(Path(argv[2]).read_text())
    trials = sorted(d for d in job.glob("*__*") if (d / "result.json").is_file())
    failed = 0
    for t in trials:
        bad = check_trial(t, bmap)
        failed += bool(bad)
        print(f"{t.name}: {'ok' if not bad else 'FAIL: ' + '; '.join(bad)}")
    ok = bool(trials) and not failed
    print(f"BLEND_CHECK: {'ok' if ok else 'FAIL'} trials={len(trials)} failed={failed}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
