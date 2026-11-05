"""Descriptive paired exact sign-flip comparisons for cluster2 exploratory arms."""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from analyze_matrix import signflip_p
from analyze_official import signflip_ci

CONTROL = "fm-tasks-control"
HM_RUNS = ("fm-tasks-run1", "fm-tasks-run2", "fm-tasks-run3")


def read_set(root: Path, name: str) -> list[dict]:
    path = root / f"summary-{name}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def task_rates(rows: list[dict], *, expected_attempts: int = 3,
               exclude_model_unavailable: bool = False, require_complete: bool = True) -> dict[str, float]:
    grouped: dict[str, list[dict]] = collections.defaultdict(list)
    for row in rows:
        if row.get("valid") is not True or row.get("finished") is not True:
            raise ValueError("exploratory set contains unfinished or invalid rows")
        if not isinstance(row.get("model_unavailable"), bool):
            raise ValueError("exploratory set has missing model-availability status")
        if exclude_model_unavailable and row["model_unavailable"]:
            continue
        task = str(row.get("task") or "").split("/")[-1]
        grouped[task].append(row)
    if require_complete and (len(grouped) != 15 or any(len(items) != expected_attempts for items in grouped.values())):
        raise ValueError(f"exploratory set must contain {expected_attempts} valid attempts for each of 15 tasks")
    if any(len(items) > expected_attempts for items in grouped.values()):
        raise ValueError("exploratory set contains too many attempts for a task")
    return {task: sum(bool(row.get("passed")) for row in items) / len(items) for task, items in grouped.items()}


def compare(arm: dict[str, float], baseline: dict[str, float], *, require_all: bool = True) -> dict:
    tasks = sorted(set(arm) & set(baseline))
    if require_all and len(tasks) != 15:
        raise ValueError("paired comparison does not cover the required tasks")
    if not tasks:
        return {
            "tasks": 0,
            "mean_pass_rate_difference": None,
            "exact_one_sided_signflip_p": None,
            "exact_95_interval": None,
            "tasks_up": 0,
            "tasks_down": 0,
            "per_task_difference": {},
        }
    diff = [arm[t] - baseline[t] for t in tasks]
    lo, hi = signflip_ci(diff)
    return {
        "tasks": len(tasks),
        "mean_pass_rate_difference": sum(diff) / len(diff),
        "exact_one_sided_signflip_p": signflip_p(diff),
        "exact_95_interval": [lo, hi],
        "tasks_up": sum(x > 0 for x in diff),
        "tasks_down": sum(x < 0 for x in diff),
        "per_task_difference": dict(zip(tasks, diff)),
    }


def unavailable_counts(rows: list[dict]) -> dict[str, int]:
    return {
        "trials": len(rows),
        "model_unavailable": sum(row.get("model_unavailable") is True for row in rows),
        "unknown_status": sum(not isinstance(row.get("model_unavailable"), bool) for row in rows),
    }


def harness_memory_effects(root: Path) -> dict | None:
    names = {
        "A0": "fm-tasks-control",
        "HM1": "fm-tasks-run1",
        "HM2": "fm-tasks-run2",
        "HM3": "fm-tasks-run3",
        "C0": "fm-tasks-codex-c0",
        "CM": "fm-tasks-codex-cm",
        "K0": "fm-tasks-claude-k0",
        "KM": "fm-tasks-claude-km",
    }
    if any(not (root / f"summary-{name}.jsonl").is_file() for name in names.values()):
        return None

    rates = {arm: task_rates(read_set(root, name)) for arm, name in names.items() if arm not in ("HM1", "HM2", "HM3")}
    hm_rows = [row for arm in ("HM1", "HM2", "HM3") for row in read_set(root, names[arm])]
    rates["HM"] = task_rates(hm_rows, expected_attempts=9)
    effects = {
        "Hermes_HM_minus_A0": {t: rates["HM"][t] - rates["A0"][t] for t in sorted(rates["A0"])},
        "Codex_CM_minus_C0": {t: rates["CM"][t] - rates["C0"][t] for t in sorted(rates["C0"])},
        "Claude_Code_KM_minus_K0": {t: rates["KM"][t] - rates["K0"][t] for t in sorted(rates["K0"])},
    }
    pairs = (
        ("Codex_minus_Hermes", "Codex_CM_minus_C0", "Hermes_HM_minus_A0"),
        ("Claude_Code_minus_Hermes", "Claude_Code_KM_minus_K0", "Hermes_HM_minus_A0"),
        ("Claude_Code_minus_Codex", "Claude_Code_KM_minus_K0", "Codex_CM_minus_C0"),
    )
    per_task = {}
    for task in sorted(set.intersection(*(set(value) for value in effects.values()))):
        per_task[task] = {name: values[task] for name, values in effects.items()}
        for pair, high, low in pairs:
            per_task[task][pair] = effects[high][task] - effects[low][task]

    def describe(values: list[float]) -> dict:
        return {
            "tasks": len(values),
            "mean_difference": sum(values) / len(values) if values else None,
            "tasks_up": sum(value > 0 for value in values),
            "tasks_down": sum(value < 0 for value in values),
        }

    pair_summaries = {
        pair: describe([per_task[t][pair] for t in sorted(per_task)])
        for pair, _, _ in pairs
    }
    return {
        "classification": "descriptive_only_no_significance_tests",
        "tasks": len(per_task),
        "per_task_memory_effects_and_pairwise_differences": per_task,
        "pairwise_difference_summaries": pair_summaries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--arm", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--dir", type=Path, required=True)
    args = parser.parse_args()
    arm_rows = read_set(args.dir, args.summary)
    control_rows = read_set(args.dir, CONTROL)
    hm1_rows = read_set(args.dir, HM_RUNS[0])
    hm_rows = [row for name in HM_RUNS for row in read_set(args.dir, name)]
    arm = task_rates(arm_rows)
    control = task_rates(control_rows)
    hm1 = task_rates(hm1_rows)
    hm = task_rates(hm_rows, expected_attempts=9)
    result = {
        "arm": args.arm,
        "summary": args.summary,
        "model_unavailable_counts": {
            args.arm: unavailable_counts(arm_rows),
            "A0": unavailable_counts(control_rows),
            "HM1": unavailable_counts(hm1_rows),
            "HM_pooled_runs_1_to_3": unavailable_counts(hm_rows),
        },
        "per_task_pass_rates": {args.arm: arm, "A0": control, "HM1": hm1, "HM_pooled_runs_1_to_3": hm},
        "comparisons": {
            "against_A0": compare(arm, control),
            "against_HM1": compare(arm, hm1),
            "against_HM_pooled_runs_1_to_3": compare(arm, hm),
        },
        "sensitivity_without_model_unavailable": {
            "against_A0": compare(
                task_rates(arm_rows, exclude_model_unavailable=True, require_complete=False),
                task_rates(control_rows, exclude_model_unavailable=True, require_complete=False), require_all=False),
            "against_HM1": compare(
                task_rates(arm_rows, exclude_model_unavailable=True, require_complete=False),
                task_rates(hm1_rows, exclude_model_unavailable=True, require_complete=False), require_all=False),
            "against_HM_pooled_runs_1_to_3": compare(
                task_rates(arm_rows, exclude_model_unavailable=True, require_complete=False),
                task_rates(hm_rows, expected_attempts=9, exclude_model_unavailable=True, require_complete=False),
                require_all=False),
        },
    }
    own_controls = {"codex-cm": "codex-c0", "claude-km": "claude-k0"}
    if args.arm in own_controls:
        own_control_name = f"fm-tasks-{own_controls[args.arm]}"
        own_control_rows = read_set(args.dir, own_control_name)
        own_control = task_rates(own_control_rows)
        result["within_harness_memory_effect"] = {
            "memory_arm": args.arm,
            "control_arm": own_controls[args.arm],
            "comparison": compare(arm, own_control),
            "model_unavailable_counts": {
                args.arm: unavailable_counts(arm_rows),
                own_controls[args.arm]: unavailable_counts(own_control_rows),
            },
            "sensitivity_without_model_unavailable": compare(
                task_rates(arm_rows, exclude_model_unavailable=True, require_complete=False),
                task_rates(own_control_rows, exclude_model_unavailable=True, require_complete=False),
                require_all=False),
        }
    cross_harness = harness_memory_effects(args.dir)
    if cross_harness is not None:
        cross_path = args.dir / "analysis-harness-memory-effects.json"
        cross_path.write_text(json.dumps(cross_harness, sort_keys=True, indent=1) + "\n")
        result["cross_harness_memory_effects"] = cross_harness
    out = args.dir / f"analysis-{args.arm.replace('/', '-')}.json"
    out.write_text(json.dumps(result, sort_keys=True, indent=1) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "comparisons"}, sort_keys=True))
    for section in ("comparisons", "sensitivity_without_model_unavailable"):
        for name, stats in result[section].items():
            print(section, name, json.dumps({key: value for key, value in stats.items() if key != "per_task_difference"}, sort_keys=True))
    if "within_harness_memory_effect" in result:
        stats = result["within_harness_memory_effect"]["comparison"]
        print("within_harness_memory_effect", json.dumps({key: value for key, value in stats.items() if key != "per_task_difference"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
