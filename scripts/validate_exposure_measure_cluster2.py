#!/usr/bin/env python3
"""Validate count-only U5 exposure reports against the finished trial summary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict]:
    values = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not all(isinstance(value, dict) for value in values):
        raise ValueError("report rows must be JSON objects")
    return values


def task_id(value: object) -> str:
    return str(value or "").split("/")[-1]


def number(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate(summary_rows: list[dict], rows: list[dict], harness: str, arm: str) -> list[str]:
    errors: list[str] = []
    expected_arms = {
        "exposure-none": {"none"}, "exposure-all": {"all"},
        "delivery-cue": {"cue"}, "delivery-scoped": {"scoped"},
        "delivery-categorized": {"categorized"},
        "codex": {"none", "hm"}, "claude-code": {"none", "hm"},
    }
    if arm not in expected_arms.get(harness, set()):
        errors.append("requested arm does not match harness")
    if not summary_rows or len(rows) != len(summary_rows):
        errors.append("exposure-measure row count differs from trial summary")
    summary_by_trial = {row.get("trial"): row for row in summary_rows if isinstance(row.get("trial"), str)}
    report_by_trial = {row.get("trial"): row for row in rows if isinstance(row.get("trial"), str)}
    if len(summary_by_trial) != len(summary_rows) or len(report_by_trial) != len(rows):
        errors.append("missing or duplicate trial identity")
    if set(summary_by_trial) != set(report_by_trial):
        errors.append("exposure-measure trial identities differ from summary")
    for trial in sorted(set(summary_by_trial) & set(report_by_trial)):
        result, row = summary_by_trial[trial], report_by_trial[trial]
        if row.get("harness") != harness or row.get("arm") != arm:
            errors.append(f"{trial}: harness or arm differs")
        if task_id(row.get("task")) != task_id(result.get("task")):
            errors.append(f"{trial}: task identity differs")
        if row.get("memory_sha256") != result.get("memory_sha256"):
            errors.append(f"{trial}: memory digest differs")
        if row.get("ok") is not True:
            errors.append(f"{trial}: exposure condition did not pass")
        capture = row.get("startup_prompt_capture")
        expected_capture = "captured" if harness in {"hermes", "exposure-none", "exposure-all", "delivery-cue", "delivery-scoped", "delivery-categorized"} else "not_captured"
        if capture != expected_capture:
            errors.append(f"{trial}: startup prompt capture status differs")
        for key in ("eligible_memory_file_probes", "memory_skill_names", "startup_files_shown",
                    "startup_skills_indexed", "later_files_seen", "later_skills_seen"):
            if not number(row.get(key)):
                errors.append(f"{trial}: {key} is invalid")
        if row.get("eligible_memory_file_probes") == 0:
            errors.append(f"{trial}: no memory-file probes were eligible")
        if number(row.get("eligible_memory_file_probes")) and row["startup_files_shown"] > row["eligible_memory_file_probes"]:
            errors.append(f"{trial}: startup file count exceeds eligible probes")
        if number(row.get("memory_skill_names")) and row["startup_skills_indexed"] > row["memory_skill_names"]:
            errors.append(f"{trial}: startup skill count exceeds skill names")
        if row.get("startup_memory_md_shown") not in (True, False):
            errors.append(f"{trial}: MEMORY.md flag is invalid")
        if harness == "exposure-none" and (row.get("startup_files_shown") != 0 or row.get("startup_skills_indexed") != 0
                                            or row.get("startup_memory_md_shown") is True):
            errors.append(f"{trial}: E-none startup contains memory")
        if harness == "exposure-all" and (row.get("startup_files_shown") != row.get("eligible_memory_file_probes")
                                           or row.get("startup_memory_md_shown") is not True):
            errors.append(f"{trial}: E-all omitted eligible memory files")
        if (harness in {"exposure-none", "exposure-all", "delivery-cue", "delivery-scoped", "delivery-categorized"}
                or arm == "hm"):
            if not isinstance(row.get("memory_sha256"), str) or re.fullmatch(r"[0-9a-f]{64}", row["memory_sha256"]) is None:
                errors.append(f"{trial}: expected memory digest is missing or malformed")
        elif row.get("memory_sha256") is not None:
            errors.append(f"{trial}: no-memory harness row carries a memory digest")
    return sorted(set(errors))


def aggregate(rows: list[dict], harness: str, arm: str) -> dict:
    return {
        "harness": harness,
        "arm": arm,
        "trials": len(rows),
        "eligible_memory_file_probes": rows[0]["eligible_memory_file_probes"] if rows else 0,
        "memory_skill_names": rows[0]["memory_skill_names"] if rows else 0,
        "startup_prompt_capture": rows[0]["startup_prompt_capture"] if rows else "missing",
        "startup_files_shown_total": sum(row["startup_files_shown"] for row in rows),
        "startup_skills_indexed_total": sum(row["startup_skills_indexed"] for row in rows),
        "later_files_seen_total": sum(row["later_files_seen"] for row in rows),
        "later_skills_seen_total": sum(row["later_skills_seen"] for row in rows),
        "ok_trials": sum(row.get("ok") is True for row in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("summary", type=Path)
    parser.add_argument("measure", type=Path)
    parser.add_argument("measure_summary", type=Path)
    parser.add_argument("--harness", required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--verify-receipt", action="store_true")
    args = parser.parse_args()
    try:
        summary_rows = read_rows(args.summary)
        rows = read_rows(args.measure)
        errors = validate(summary_rows, rows, args.harness, args.arm)
        expected_summary = aggregate(rows, args.harness, args.arm)
        saved_summary = json.loads(args.measure_summary.read_text())
        if saved_summary != expected_summary:
            errors.append("exposure-measure aggregate differs from per-trial rows")
        if len({row.get("eligible_memory_file_probes") for row in rows}) != 1:
            errors.append("eligible memory-file probe count varies across trials")
        if len({row.get("memory_skill_names") for row in rows}) != 1:
            errors.append("memory skill count varies across trials")
        if errors:
            raise ValueError("; ".join(errors))
        digests = sorted({row.get("memory_sha256") for row in rows if row.get("memory_sha256")})
        if len(digests) > 1 or any(re.fullmatch(r"[0-9a-f]{64}", digest) is None for digest in digests):
            raise ValueError("memory digest is malformed or varies across trials")
        receipt = {
            "status": "pass",
            "harness": args.harness,
            "arm": args.arm,
            "trial_count": len(rows),
            "summary_sha256": sha256(args.summary),
            "measure_sha256": sha256(args.measure),
            "measure_summary_sha256": sha256(args.measure_summary),
            "memory_sha256": digests[0] if digests else None,
        }
        if args.verify_receipt:
            if json.loads(args.receipt.read_text()) != receipt:
                raise ValueError("saved exposure-measure receipt or input digests differ")
        else:
            args.receipt.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(dir=args.receipt.parent, prefix=".exposure-measure-check-")
            with os.fdopen(fd, "w") as output:
                json.dump(receipt, output, sort_keys=True)
                output.write("\n")
            os.chmod(temporary, 0o600)
            os.replace(temporary, args.receipt)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"EXPOSURE_MEASURE_CHECK_FAILED: {exc}")
        return 1
    print(f"EXPOSURE_MEASURE_CHECK_OK trials={len(rows)} harness={args.harness} arm={args.arm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
