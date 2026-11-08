"""How much of the public leaderboard's ordering is within run-to-run noise (paper RQ3, D130). Counts only.

Published scores (frontiermemory.com/blog/v1, read 2026-11-08): each is the mean full-pass rate over 15 tasks across 3
independent runs, i.e. a count out of 45 task-attempts (every score is a multiple of 1/45). Our own runs give the
variation between independent generations of the same system with the same model (runs 1, 3, 4: each a fresh memory).

1. For adjacent leaderboard entries: the gap in task-attempts, its binomial standard error (each entry 45 attempts),
   and the probability an independent rerun of both reverses their order (normal approximation).
2. Monte Carlo: how often an independent rerun of the top three reproduces their published order, with each entry's
   45 attempts drawn at its published rate. Ties count as not reproduced. Two noise levels: independent attempts
   (binomial), and binomial scaled by our observed ratio of run-to-run SD to binomial SD (same-system generations).
3. Our same-system spread: passes per run for runs 1, 3, 4, their SD, and the binomial SD at their mean rate.

    python3 -I scripts/leaderboard_noise.py [--dir results/official] [--seed 1] [--sims 200000]
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from pathlib import Path

N = 45  # task-attempts behind each published score: 15 tasks x 3 runs
PUBLISHED = [("rank 1", 73.3), ("rank 2", 71.1), ("rank 3", 68.9), ("rank 4", 64.4), ("rank 5", 51.1), ("rank 6", 51.1),
             ("rank 7", 37.8)]
SAME_SYSTEM_RUNS = ("run1", "run3", "run4")


def passes(path: Path) -> int:
    return sum(bool(json.loads(l).get("passed")) for l in open(path))


def phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(Path(__file__).resolve().parent.parent / "results" / "official"))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--sims", type=int, default=200000)
    a = ap.parse_args()
    out = {}

    k = [round(s / 100 * N) for _, s in PUBLISHED]
    assert all(abs(kk / N * 100 - s) < 0.06 for kk, (_, s) in zip(k, PUBLISHED)), "scores are not on the 1/45 grid"
    pairs = []
    for i in range(len(PUBLISHED) - 1):
        p1, p2 = k[i] / N, k[i + 1] / N
        gap = k[i] - k[i + 1]
        se = math.sqrt(p1 * (1 - p1) / N + p2 * (1 - p2) / N)
        pairs.append({"pair": f"{PUBLISHED[i][0]} vs {PUBLISHED[i + 1][0]}", "attempts": f"{k[i]} vs {k[i + 1]} of {N}",
                      "gap_attempts": gap, "gap_points": round((p1 - p2) * 100, 1), "se_points": round(se * 100, 1),
                      "p_rerun_reverses": round(1 - phi((p1 - p2) / se), 2) if gap else 0.5})
    out["adjacent_pairs"] = pairs

    runs = {r: passes(Path(a.dir) / f"summary-fm-tasks-{r}.jsonl") for r in SAME_SYSTEM_RUNS}
    m = statistics.mean(runs.values())
    sd = statistics.stdev(runs.values())
    sd_binom = math.sqrt(N * (m / N) * (1 - m / N))
    out["same_system_runs"] = {"passes_of_45": runs, "range": max(runs.values()) - min(runs.values()),
                               "sd_attempts": round(sd, 2), "binomial_sd_attempts": round(sd_binom, 2),
                               "ratio": round(sd / sd_binom, 2)}

    rng = random.Random(a.seed)
    top = [kk / N for kk in k[:3]]
    res = {}
    for label, scale in (("binomial", 1.0), ("scaled_to_our_runs", sd / sd_binom)):
        kept = 0
        for _ in range(a.sims):
            draws = []
            for p in top:  # normal approximation with the chosen scale, rounded to whole attempts
                x = round(N * p + rng.gauss(0, 1) * scale * math.sqrt(N * p * (1 - p)))
                draws.append(min(N, max(0, x)))
            kept += draws[0] > draws[1] > draws[2]
        res[label] = round(kept / a.sims, 3)
    out["p_rerun_reproduces_top3_order"] = res
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
