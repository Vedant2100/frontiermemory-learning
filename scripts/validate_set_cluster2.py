"""Fail-closed checks for cluster2 set summaries; counts and digests only."""
from __future__ import annotations

import argparse
import collections
import json
import math
import re
from pathlib import Path
from collections.abc import Sequence

# Public task IDs from the checksum-verified pinned v1.0 task release.
TASKS = frozenset("""
apex-brightpath-market-share apex-brightpath-seat-surplus apex-eurogrid-curtailment
automationbench-marketing-content-gap-analysis automationbench-sales-chatgpt-proposal-customization
automationbench-sales-partnership-contract awilix-release-tier-explicit awilix-release-tier-implicit
build-word2vec-pipeline cattrs-compositional-changelog cookie-store-compositional-changelog
customer-delivery-contextual-preferences dapt-intrusion-detection-workflow-learning
enterpriseops-csm-26d1b04a enterpriseops-teams-2725d17f
""".split())


def read_rows(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("each summary row must be an object")
    return rows


def validate(rows: list[dict], kind: str, *, task: str | None = None,
             tasks: Sequence[str] | None = None, attempts: int | None = None,
             expected_memory: str | None = None) -> list[str]:
    errors: list[str] = []
    if task is not None and tasks is not None:
        errors.append("select either one task or a task list")
    wanted = {task} if task is not None else (set(tasks) if tasks is not None else TASKS)
    if attempts is None:
        attempts = 1 if task is not None or tasks is not None else 3
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 1:
        errors.append("attempt count must be a positive integer")
        attempts = 1
    if not wanted <= TASKS:
        errors.append("unknown requested task")
    counts = collections.Counter((r.get("task") or "").split("/")[-1] for r in rows)
    if counts != collections.Counter({t: attempts for t in wanted}):
        errors.append("task identities or attempt counts differ")
    trials = [r.get("trial") for r in rows]
    if any(not isinstance(t, str) or not t for t in trials) or len(set(trials)) != len(trials):
        errors.append("missing or duplicate trial identifiers")
    for r in rows:
        name = (r.get("task") or "").split("/")[-1]
        if r.get("finished") is not True or r.get("valid") is not True:
            errors.append("unfinished or invalid trial")
        reward = r.get("reward")
        if isinstance(reward, bool) or not isinstance(reward, (int, float)) or not math.isfinite(reward):
            errors.append("missing or non-finite reward")
        elif not isinstance(r.get("passed"), bool) or r["passed"] != (reward >= 1):
            errors.append("pass flag inconsistent with reward")
        if not isinstance(r.get("model_unavailable"), bool):
            errors.append("model availability status missing")
        judge = r.get("judge_status")
        if (name.startswith("apex-") and judge != "completed") or (judge not in (None, "completed")):
            errors.append("judge missing or incomplete; regrade before proceeding")
    digests = {r.get("memory_sha256") for r in rows}
    if kind == "control":
        if digests != {None}:
            errors.append("control has memory or no rows")
    else:
        if len(digests) != 1 or not all(isinstance(d, str) and re.fullmatch(r"[0-9a-f]{64}", d) for d in digests):
            errors.append("memory digest missing, malformed or inconsistent")
        if expected_memory is not None and digests != {expected_memory}:
            errors.append("memory digest differs from selected generation")
        if kind == "exposure" and expected_memory is None:
            errors.append("exposure requires selected generation digest")
    return sorted(set(errors))


def main() -> int:
    p = argparse.ArgumentParser(description="Validate a cluster2 run summary without showing trial content")
    p.add_argument("summary", type=Path)
    p.add_argument("--kind", choices=("control", "memory", "exposure"), required=True)
    selected = p.add_mutually_exclusive_group()
    selected.add_argument("--task", help="one exact public task ID for an uncounted one-trial check")
    selected.add_argument("--tasks", nargs="+", help="exact public task IDs for an uncounted subset")
    p.add_argument("--attempts", type=int, help="attempts per selected task (defaults to 1 for subsets, 3 for all tasks)")
    p.add_argument("--expected-memory", help="the selected generation's SHA-256 digest")
    args = p.parse_args()
    try:
        rows = read_rows(args.summary)
        errors = validate(rows, args.kind, task=args.task, tasks=args.tasks, attempts=args.attempts,
                          expected_memory=args.expected_memory)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        print("SET_CHECK_FAILED: unreadable or malformed summary")
        return 1
    if errors:
        print("SET_CHECK_FAILED: " + "; ".join(errors))
        return 1
    print(f"SET_CHECK_OK: {len(rows)} valid, finished trials across {len({r['task'] for r in rows})} tasks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
