"""Preregistered analysis of the official-setup study (results/preregistration-v2.md).

Primary: strict pass. One-sided exact paired sign-flip over tasks on the per-task difference in strict pass rate
(HM minus A0), with HM attempts pooled over runs within a task. Reads results/official/summary-*.jsonl, one line per trial.
A trial with no reward is an infrastructure failure, so a set containing one is flagged and not analysed as final.
Writes results/official/analysis.json. Usage: python3 -I scripts/analyze_official.py [--dir DIR] [--test]
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_left, bisect_right
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from analyze_matrix import clopper_pearson, signflip_p  # noqa: E402

CONTROL, RUNS = "fm-tasks-control", ("fm-tasks-run1", "fm-tasks-run2", "fm-tasks-run3")
EXPECTED_ATTEMPTS, N_TASKS = 3, 15
NO_REFERENCE_PASS = {"cattrs-compositional-changelog", "cookie-store-compositional-changelog",
                     "enterpriseops-csm-26d1b04a", "enterpriseops-teams-2725d17f"}


def signflip_ci(d: list[float], alpha: float = 0.05) -> tuple[float | None, float | None]:
    """Two-sided exact interval for the mean difference, by inverting the sign-flip test.

    Same test as analyze_matrix.signflip_ci, which is too slow at 15 tasks. A pattern's statistic at shift delta is
    S - delta * (sum of its signs), so patterns are grouped by their count of plus signs and each group's S values sorted once.
    Each candidate shift is then a binary search per group. Returns (None, None) when too few tasks bound the interval.
    """
    n = len(d)
    groups: dict[int, list[float]] = defaultdict(list)
    for mask in range(1 << n):
        groups[bin(mask).count("1")].append(sum(v if mask >> i & 1 else -v for i, v in enumerate(d)))
    for g in groups.values():
        g.sort()

    def two_sided_p(delta: float) -> float:
        observed = sum(v - delta for v in d)
        up = down = 0
        for plus, sums in groups.items():
            shift = delta * (2 * plus - n)  # the sum of signs is plus - (n - plus)
            up += len(sums) - bisect_left(sums, observed + shift - 1e-12)
            down += bisect_right(sums, observed + shift + 1e-12)
        return min(1.0, 2 * min(up, down) / (1 << n))

    lo_b, hi_b = min(d) - 1, max(d) + 1
    grid = sorted({lo_b + i * (hi_b - lo_b) / 2000 for i in range(2001)} | {0.0, *d})
    keep = [x for x in grid if two_sided_p(x) > alpha]
    if not keep or keep[0] == grid[0] or keep[-1] == grid[-1]:
        return (None, None)
    return (keep[0], keep[-1])


def read_set(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def task_name(row: dict) -> str:
    return (row.get("task") or "").split("/")[-1]


def tally(rows: list[dict]) -> dict[str, list[int]]:
    """task -> [passes, valid trials]. Passing is reward >= 1, as in the official scorer."""
    out: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        if row.get("reward") is None:
            continue
        out[task_name(row)][0] += int(float(row["reward"]) >= 1.0)
        out[task_name(row)][1] += 1
    return out


def check_set(name: str, rows: list[dict]) -> list[str]:
    flags = []
    if bad := [r for r in rows if r.get("reward") is None]:
        flags.append(f"{name}: {len(bad)} trial(s) with no reward")
    counts = tally(rows)
    if len(counts) != N_TASKS:
        flags.append(f"{name}: {len(counts)} tasks, expected {N_TASKS}")
    if off := {t: c[1] for t, c in counts.items() if c[1] != EXPECTED_ATTEMPTS}:
        flags.append(f"{name}: attempts differ from {EXPECTED_ATTEMPTS}: {off}")
    digests = {r.get("memory_sha256") for r in rows}
    if name == CONTROL and digests - {None}:
        flags.append(f"{name}: a control trial has a memory digest")
    if name != CONTROL and (None in digests or len(digests) != 1):
        flags.append(f"{name}: expected one memory digest on every trial, got {sorted(map(str, digests))}")
    return flags


def compare(control: dict, memory: dict, tasks: list[str]) -> dict:
    diffs = [memory[t][0] / memory[t][1] - control[t][0] / control[t][1] for t in tasks]
    lo, hi = signflip_ci(diffs)
    return {"tasks": len(tasks), "mean_diff": sum(diffs) / len(diffs), "ci95": [lo, hi], "p_one_sided": signflip_p(diffs),
            "per_task": dict(zip(tasks, diffs)), "tasks_up": sum(d > 0 for d in diffs), "tasks_down": sum(d < 0 for d in diffs)}


def analyse(sets: dict[str, list[dict]]) -> dict:
    flags = [f for name, rows in sets.items() for f in check_set(name, rows)]
    runs = [r for r in RUNS if r in sets]
    if CONTROL not in sets or not runs:
        return {"flags": flags + ["need the control and at least one run"]}
    if len(runs) < len(RUNS):
        flags.append(f"only {len(runs)} of {len(RUNS)} runs: state the shortfall (prereg)")
    control = tally(sets[CONTROL])
    memory: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in runs:
        for task, (k, n) in tally(sets[r]).items():
            memory[task][0] += k
            memory[task][1] += n
    tasks = sorted(t for t in control if memory[t][1] and control[t][1])
    pooled = {arm: (sum(v[0] for v in d.values()), sum(v[1] for v in d.values())) for arm, d in (("A0", control), ("HM", memory))}
    return {"runs_used": runs, "flags": flags, "primary": compare(control, memory, tasks),
            "sensitivity_without_no_reference_tasks": compare(control, memory, [t for t in tasks if t not in NO_REFERENCE_PASS]),
            "pooled": {arm: {"pass": k, "n": n, "ci95": list(clopper_pearson(k, n)) if n else None} for arm, (k, n) in pooled.items()},
            "per_task": {t: {"A0": control[t], "HM": memory[t]} for t in tasks},
            "per_run_pass": {r: sum(v[0] for v in tally(sets[r]).values()) for r in runs}}


def self_test() -> None:
    def rows(job, passes, digest=None, attempts=3):
        return [{"task": f"letta-ai/t{i}", "reward": float(a < p), "memory_sha256": digest}
                for i, p in enumerate(passes) for a in range(attempts)]
    n = N_TASKS
    a0 = rows(CONTROL, [0] * n)
    run = rows(RUNS[0], [1] * 5 + [0] * (n - 5), "abc")
    r = analyse({CONTROL: a0, RUNS[0]: run})
    assert abs(r["primary"]["p_one_sided"] - 1 / 32) < 1e-12, r["primary"]["p_one_sided"]  # 5 tasks up, none down
    assert r["pooled"]["HM"]["pass"] == 5 and r["pooled"]["A0"]["pass"] == 0 and r["primary"]["tasks_up"] == 5
    assert any("only 1 of 3" in f for f in r["flags"])
    r = analyse({CONTROL: rows(CONTROL, [3] + [0] * (n - 1)), RUNS[0]: rows(RUNS[0], [0] * n, "abc")})
    assert abs(r["primary"]["p_one_sided"] - 1.0) < 1e-12 and r["primary"]["tasks_down"] == 1  # only a loss: no evidence for memory
    r = analyse({CONTROL: a0, RUNS[0]: rows(RUNS[0], [1] * n, "abc"), RUNS[1]: rows(RUNS[1], [0] * n, "abc"), RUNS[2]: rows(RUNS[2], [0] * n, "abc")})
    assert abs(r["primary"]["mean_diff"] - 1 / 9) < 1e-12  # pooled over runs: 1 pass of 9 per task
    assert not [f for f in r["flags"] if "attempts" in f or "digest" in f]
    bad = a0[:-1] + [{**a0[-1], "reward": None}]
    assert any("no reward" in f for f in check_set(CONTROL, bad)) and any("attempts differ" in f for f in check_set(CONTROL, bad))
    assert any("digest" in f for f in check_set(RUNS[0], rows(RUNS[0], [0] * n, None)))
    assert any("control trial" in f for f in check_set(CONTROL, rows(CONTROL, [0] * n, "abc")))
    import analyze_matrix  # the fast interval must equal the slow, already-reviewed one where that is feasible
    for d in ([0.5, 0.2, -0.1, 0.3, 0.0, 0.4, 0.1], [1, 0, 0, 0, 0, 0], [0.1, -0.2, 0.3, 0.05, 0.2, 0.4, 0.15, 0.25]):
        fast, slow = signflip_ci(d), analyze_matrix.signflip_ci(d)
        assert (fast[0] is None) == (slow[0] is None), (d, fast, slow)
        if fast[0] is not None:
            assert abs(fast[0] - slow[0]) < 1e-9 and abs(fast[1] - slow[1]) < 1e-9, (d, fast, slow)
    print("self-test passed")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", type=Path, default=REPO / "results/official")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()
    if args.test:
        return self_test()
    sets = {n: read_set(args.dir / f"summary-{n}.jsonl") for n in (CONTROL, *RUNS) if (args.dir / f"summary-{n}.jsonl").exists()}
    out = analyse(sets)
    (args.dir / "analysis.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out.get(k) for k in ("runs_used", "flags", "pooled", "per_run_pass")}, indent=1))
    for k in ("primary", "sensitivity_without_no_reference_tasks"):
        if k in out:
            print(k, {x: out[k][x] for x in ("tasks", "mean_diff", "ci95", "p_one_sided", "tasks_up", "tasks_down")})


if __name__ == "__main__":
    main()
