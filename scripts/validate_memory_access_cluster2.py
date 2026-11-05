"""Fail-closed count and identity validation for per-trial memory-access reports."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path


def rows(path: Path) -> list[dict]:
    values = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not all(isinstance(value, dict) for value in values):
        raise ValueError("rows must be JSON objects")
    return values


def task_id(value: object) -> str:
    return str(value or "").split("/")[-1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(summary: list[dict], access: list[dict], harness: str, kind: str) -> list[str]:
    errors: list[str] = []
    shown_rules = {
        "hermes": "hermes_full_memory_index",
        "codex": "codex_2500_token_head_tail_4_bytes_per_token",
        "claude-code": "claude_first_200_lines_or_25_kib",
        "exposure-none": "exposure_none",
        "exposure-all": "hm_memory_md_plus_observed_memory_skill_index_plus_full_file_injection",
        "delivery-cue": "cue_confirmed_skill_text_present_in_next_request",
        "delivery-scoped": "memory_md_plus_observed_memory_skill_entries_and_source_headers",
        "delivery-categorized": "memory_md_plus_categorized_memory_entries_and_source_and_category_headers",
    }
    if not summary or len(summary) != len(access):
        errors.append("memory-access row count differs from trial summary")
    summary_by_trial = {row.get("trial"): row for row in summary if isinstance(row.get("trial"), str)}
    access_by_trial = {row.get("trial"): row for row in access if isinstance(row.get("trial"), str)}
    if len(summary_by_trial) != len(summary) or len(access_by_trial) != len(access):
        errors.append("missing or duplicate trial identity")
    if set(summary_by_trial) != set(access_by_trial):
        errors.append("memory-access trial identities differ from trial summary")
    for trial in sorted(set(summary_by_trial) & set(access_by_trial)):
        result = summary_by_trial[trial]
        metric = access_by_trial[trial]
        if metric.get("harness") != harness:
            errors.append(f"{trial}: harness identity differs")
        if task_id(result.get("task")) != task_id(metric.get("task")):
            errors.append(f"{trial}: task identity differs")
        reward = result.get("reward")
        access_reward = metric.get("reward")
        if (isinstance(reward, bool) or not isinstance(reward, (int, float)) or not math.isfinite(reward)
                or isinstance(access_reward, bool) or not isinstance(access_reward, (int, float))
                or not math.isfinite(access_reward) or not math.isclose(reward, access_reward, rel_tol=0, abs_tol=1e-9)):
            errors.append(f"{trial}: reward differs or is invalid")
        digest = result.get("memory_sha256")
        if metric.get("memory_sha256") != digest:
            errors.append(f"{trial}: memory digest differs")
        if kind == "control" and metric.get("has_memory") is not False:
            errors.append(f"{trial}: control memory-presence flag is not false")
        if not isinstance(metric.get("has_memory"), bool):
            errors.append(f"{trial}: memory-presence flag is missing")
        elif digest is not None and not metric["has_memory"]:
            errors.append(f"{trial}: digest is present but memory is marked absent")
        if not isinstance(metric.get("opened"), bool):
            errors.append(f"{trial}: memory-open flag is missing")
        opens = metric.get("opens")
        if isinstance(opens, bool) or not isinstance(opens, int) or opens < 0:
            errors.append(f"{trial}: memory-open count is invalid")
        elif metric.get("opened") != (opens > 0):
            errors.append(f"{trial}: memory-open flag/count disagree")
        shown_bytes = metric.get("shown_bytes_estimate")
        shown_tokens = metric.get("shown_tokens_estimate")
        if digest is not None:
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                errors.append(f"{trial}: summary memory digest is malformed")
            if isinstance(shown_bytes, bool) or not isinstance(shown_bytes, int) or shown_bytes < 0:
                errors.append(f"{trial}: shown-byte estimate is missing")
            if isinstance(shown_tokens, bool) or not isinstance(shown_tokens, int) or shown_tokens < 0:
                errors.append(f"{trial}: shown-token estimate is missing")
            elif not isinstance(shown_bytes, bool) and isinstance(shown_bytes, int) and shown_tokens != round(shown_bytes / 4):
                errors.append(f"{trial}: shown-token estimate differs from byte estimate")
            if metric.get("shown_rule") != shown_rules.get(harness):
                errors.append(f"{trial}: shown rule does not match harness")
            if harness.startswith("exposure-") and metric.get("exposure") != harness.removeprefix("exposure-"):
                errors.append(f"{trial}: exposure identity differs from harness")
            if harness.startswith("delivery-") and metric.get("delivery") != harness.removeprefix("delivery-"):
                errors.append(f"{trial}: delivery identity differs from harness")
            if harness == "exposure-all":
                parts = (metric.get("hm_startup_memory_md_bytes"),
                         metric.get("hm_startup_memory_skill_entries_bytes"),
                         metric.get("hm_startup_memory_skill_source_header_bytes"),
                         metric.get("exposure_injected_bytes"))
                if (any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in parts)
                        or metric.get("shown_bytes_estimate") != sum(parts)):
                    errors.append(f"{trial}: E-all shown bytes do not include ordinary HM exposure and injection")
            if harness.startswith("delivery-") and harness != "delivery-cue":
                if harness == "delivery-categorized":
                    parts = (metric.get("hm_startup_memory_md_bytes"),
                             metric.get("hm_startup_memory_skill_entries_bytes"),
                             metric.get("hm_startup_memory_skill_source_header_bytes"),
                             metric.get("hm_startup_memory_skill_category_header_bytes"))
                else:
                    parts = (metric.get("hm_startup_memory_md_bytes"),
                             metric.get("hm_startup_memory_skill_entries_bytes"),
                             metric.get("hm_startup_memory_skill_source_header_bytes"))
                if (any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in parts)
                        or metric.get("shown_bytes_estimate") != sum(parts)):
                    errors.append(f"{trial}: delivery shown bytes do not match observed HM startup content")
        elif shown_bytes is not None or shown_tokens is not None or metric.get("opened"):
            errors.append(f"{trial}: no-memory trial reports shown or opened memory")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("summary", type=Path)
    parser.add_argument("memory_access", type=Path)
    parser.add_argument("--harness", required=True)
    parser.add_argument("--kind", choices=("control", "memory", "exposure"), required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--verify-receipt", action="store_true", help="verify an existing receipt without replacing it")
    args = parser.parse_args()
    try:
        summary_rows = rows(args.summary)
        access_rows = rows(args.memory_access)
        errors = validate(summary_rows, access_rows, args.harness, args.kind)
        if errors:
            print("MEMORY_ACCESS_CHECK_FAILED: " + "; ".join(errors))
            return 1
        digest_values = {row.get("memory_sha256") for row in summary_rows}
        memory_digests = sorted(value for value in digest_values if value)
        if args.kind == "control" and digest_values != {None}:
            raise ValueError("control summary contains a memory digest")
        if args.kind != "control" and (len(digest_values) != 1 or len(memory_digests) != 1
                                        or re.fullmatch(r"[0-9a-f]{64}", memory_digests[0]) is None):
            raise ValueError("memory summary must contain one valid digest on every trial")
        receipt = {
            "status": "pass",
            "harness": args.harness,
            "kind": args.kind,
            "trial_count": len(summary_rows),
            "summary_sha256": sha256(args.summary),
            "memory_access_sha256": sha256(args.memory_access),
            "memory_sha256": memory_digests[0] if memory_digests else None,
        }
        if args.verify_receipt:
            saved = json.loads(args.receipt.read_text())
            if saved != receipt:
                raise ValueError("existing memory-access receipt or its input digests differ")
        else:
            args.receipt.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(dir=args.receipt.parent, prefix=".memory-access-check-")
            with os.fdopen(fd, "w") as output:
                json.dump(receipt, output, sort_keys=True)
                output.write("\n")
            os.chmod(name, 0o600)
            os.replace(name, args.receipt)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"MEMORY_ACCESS_CHECK_FAILED: {exc}")
        return 1
    print(f"MEMORY_ACCESS_CHECK_OK trials={len(summary_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
