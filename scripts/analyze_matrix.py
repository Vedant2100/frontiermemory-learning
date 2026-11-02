"""Preregistered analysis of the confirmatory matrix (prereg-v1 §4 as amended by A3/A5).

Primary: strict pass. H0: M3 > A0 and H1: M3 > R25, each a one-sided exact paired sign-flip permutation
test over tasks on the per-task difference in strict pass rate, Holm-corrected across the two.
Secondary: the same test on the hidden-test fraction (official suite only; agent-written tests excluded, D58).
Effect sizes: mean per-task difference with an exact 95% interval by inverting the same sign-flip test,
plus Clopper-Pearson intervals for each arm's pooled pass rate.

Only the jobs listed in JOBS count. Lost or superseded jobs (e.g. 303384) are never read.
Usage: python3 -I scripts/analyze_matrix.py [--out results/matrix-v1-analysis.json]
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
R = REPO / "results"
ARMS = ("A0", "R25", "M3")
CONTRASTS = {"H0": ("M3", "A0"), "H1": ("M3", "R25")}

# task -> (job dir, total hidden tests). One confirmatory job per task.
JOBS = {
    "build-word2vec-pipeline": (R / "word2vec-codex-ollama/job-303281", 6),
    "dapt-intrusion-detection-workflow-learning": (R / "frontiermemory-dapt/codex-ollama-job-303282", 37),
    "awilix-release-tier-implicit": (R / "awilix-release-tier-implicit-codex-ollama/job-303363", 184),
    "awilix-release-tier-explicit": (R / "awilix-release-tier-explicit-codex-ollama/job-303383", 184),
    "customer-delivery-contextual-preferences": (R / "customer-delivery-codex-ollama/job-304910", 188),
    "cattrs-compositional-changelog": (R / "cattrs-codex-ollama/job-304911", 77),
    "cookie-store-compositional-changelog": (R / "cookie-store-codex-ollama/job-304912", 1400),
}

AWILIX_BASE_FILES = {"function-tokenizer", "param-parser.bugs", "param-parser", "utils", "list-modules",
                     "load-modules", "container.disposing", "resolvers", "local-injections", "container",
                     "lifetime", "inheritance", "awilix", "integration", "rollup"}


def awilix_hidden(tdir: Path) -> int | None:
    """D58: 161 base tests when all 15 original files pass, plus functional-suite passes."""
    f = tdir / "grading/harbor-trial/verifier/test-stdout.txt"
    if not f.exists():
        return None
    base, _, func = f.read_text(errors="ignore").partition("Step 4: Running new tests")
    files = re.findall(r"^(PASS|FAIL) src/__tests__/(\S+?)\.test\.[jt]s", base, re.M)
    orig = {n: st for st, n in files if n in AWILIX_BASE_FILES}
    if len(orig) != 15 or any(st != "PASS" for st in orig.values()):
        return None  # an original file failed: needs a manual per-test count
    m = re.findall(r"^Tests:\s+.*?(\d+) passed", func, re.M)
    return 161 + (int(m[-1]) if m else 0)


TEST_PATH = re.compile(r"(^|/)(tests?|__tests__)/|(^|/)test_[^/]*\.py$|_test\.py$|\.test\.[jt]sx?$|\.spec\.[jt]sx?$")


def patch_touches_tests(tdir: Path) -> bool:
    patch = tdir / "model.patch"
    if not patch.exists():
        return False
    paths = re.findall(r"^diff --git a/(\S+)", patch.read_text(errors="ignore"), re.M)
    return any(TEST_PATH.search(p) for p in paths)


def hidden_passed(task: str, tdir: Path, rec: dict, total: int | None) -> int | None:
    if rec["failure_category"] in ("NO_ARTIFACT",) or not rec.get("verifier_collected"):
        return 0  # D5'/D43: an agent failure scores 0, even if the untouched base suite would pass
    rw = tdir / "grading/harbor-trial/verifier/reward.json"
    j = json.loads(rw.read_text()) if rw.exists() else {}
    if "p2p_total" in j and "f2p_total" in j:  # grader reports official-suite counts itself (customer-delivery)
        assert total is None or j["p2p_total"] + j["f2p_total"] == total, f"{tdir}: official total mismatch"
        return j["p2p_passed"] + j["f2p_passed"]
    if not patch_touches_tests(tdir):
        return rec["verifier_passed"]  # the agent added or edited no test file: every counted test is hidden
    if task.startswith("awilix"):
        return awilix_hidden(tdir)
    return None  # agent touched tests on a task without an extractor yet: flagged, never guessed


def load(task: str):
    job, total = JOBS[task]
    trials = []
    for rf in sorted(job.glob("trial-*/trial-record.json")):
        rec = json.loads(rf.read_text())
        if not rec.get("valid"):
            continue
        hp = hidden_passed(task, rf.parent, rec, total)
        trials.append({"arm": rec["arm"], "pass": int(rec["strict_reward"] == 1.0), "hidden": hp,
                       "total": total, "trial": rec["trial_index"]})
    return trials


def signflip_p(d: list[float]) -> float:
    """One-sided exact p: share of sign patterns whose mean is >= the observed mean."""
    obs = sum(d)
    n = len(d)
    hits = sum(1 for s in itertools.product((1, -1), repeat=n) if sum(a * b for a, b in zip(s, d)) >= obs - 1e-12)
    return hits / 2 ** n


def signflip_ci(d: list[float], alpha: float = 0.05) -> tuple[float, float]:
    """Two-sided exact interval for the mean difference by test inversion over a grid of shifts."""
    lo_b, hi_b = min(d) - 1, max(d) + 1
    grid = [lo_b + i * (hi_b - lo_b) / 2000 for i in range(2001)]
    keep = []
    for delta in grid:
        x = [v - delta for v in d]
        p_up = signflip_p(x)
        p_dn = signflip_p([-v for v in x])
        if min(1.0, 2 * min(p_up, p_dn)) > alpha:
            keep.append(delta)
    if not keep or keep[0] == grid[0] or keep[-1] == grid[-1]:
        return (None, None)  # too few tasks to reject any shift: the interval is unbounded
    return (min(keep), max(keep))


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    def betainc_cdf(x, a, b):  # regularized incomplete beta via binomial sum (integer a, b)
        m = a + b - 1
        return sum(math.comb(m, j) * x ** j * (1 - x) ** (m - j) for j in range(a, m + 1))

    def solve(target, a, b):
        lo, hi = 0.0, 1.0
        for _ in range(100):
            mid = (lo + hi) / 2
            (lo, hi) = (mid, hi) if betainc_cdf(mid, a, b) < target else (lo, mid)
        return (lo + hi) / 2
    lower = 0.0 if k == 0 else solve(alpha / 2, k, n - k + 1)
    upper = 1.0 if k == n else solve(1 - alpha / 2, k + 1, n - k)
    return lower, upper


def holm(ps: dict[str, float]) -> dict[str, float]:
    order = sorted(ps, key=ps.get)
    adj, running = {}, 0.0
    for i, h in enumerate(order):
        running = max(running, min(1.0, (len(order) - i) * ps[h]))
        adj[h] = running
    return adj


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(R / "matrix-v1-analysis.json"))
    args = ap.parse_args()

    per_task, flags = {}, []
    for task in JOBS:
        trials = load(task)
        if not trials:
            flags.append(f"{task}: no trials yet")
            continue
        row = {}
        for arm in ARMS:
            t = [x for x in trials if x["arm"] == arm]
            hid = [x["hidden"] for x in t]
            total = JOBS[task][1]
            row[arm] = {"n": len(t), "pass": sum(x["pass"] for x in t),
                        "hidden_mean": (sum(hid) / len(hid)) if hid and None not in hid else None}
            if None in hid:
                flags.append(f"{task} {arm}: {hid.count(None)} trial(s) need a manual hidden-test count")
            if total is None:
                flags.append(f"{task}: total hidden tests not set")
        complete = all(row[a]["n"] == 5 for a in ARMS)
        if not complete:
            flags.append(f"{task}: incomplete ({', '.join(f'{a}={row[a]['n']}' for a in ARMS)}); excluded from tests")
        per_task[task] = {"arms": row, "complete": complete, "total_hidden": JOBS[task][1]}

    done = [t for t, v in per_task.items() if v["complete"]]
    results = {}
    for metric in ("strict", "hidden_fraction"):
        ps, eff = {}, {}
        for h, (a, b) in CONTRASTS.items():
            d = []
            for t in done:
                ra, rb = per_task[t]["arms"][a], per_task[t]["arms"][b]
                if metric == "strict":
                    d.append(ra["pass"] / ra["n"] - rb["pass"] / rb["n"])
                elif None not in (ra["hidden_mean"], rb["hidden_mean"], per_task[t]["total_hidden"]):
                    d.append((ra["hidden_mean"] - rb["hidden_mean"]) / per_task[t]["total_hidden"])
            if len(d) < 2:
                continue
            ps[h] = signflip_p(d)
            lo, hi = signflip_ci(d)
            eff[h] = {"tasks": len(d), "mean_diff": sum(d) / len(d), "ci95": [lo, hi], "per_task": d}
        adj = holm(ps) if ps else {}
        results[metric] = {h: {**eff[h], "p_one_sided": ps[h], "p_holm": adj[h]} for h in ps}

    pooled = {}
    for arm in ARMS:
        k = sum(per_task[t]["arms"][arm]["pass"] for t in done)
        n = sum(per_task[t]["arms"][arm]["n"] for t in done)
        pooled[arm] = {"pass": k, "n": n, "ci95": list(clopper_pearson(k, n)) if n else None}

    out = {"tasks_complete": len(done), "tasks_listed": len(JOBS), "per_task": per_task,
           "pooled": pooled, "tests": results, "flags": flags,
           "note": "Interim unless tasks_complete == 7. Holm family: H0, H1 (prereg A3)."}
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"tasks complete: {len(done)}/{len(JOBS)}")
    for t in done:
        r = per_task[t]["arms"]
        print(f"  {t[:34]:34s} " + "  ".join(f"{a} {r[a]['pass']}/5 hid {r[a]['hidden_mean']}" for a in ARMS))
    for m, hs in results.items():
        for h, v in hs.items():
            ci = "unbounded" if v["ci95"][0] is None else f"[{v['ci95'][0]:+.3f}, {v['ci95'][1]:+.3f}]"
            print(f"  {m:15s} {h}: mean diff {v['mean_diff']:+.3f} CI {ci}"
                  f"  p={v['p_one_sided']:.4f} Holm={v['p_holm']:.4f}")
    for a, v in pooled.items():
        print(f"  pooled {a}: {v['pass']}/{v['n']}  CP95 {v['ci95']}")
    for f in flags:
        print("  FLAG", f)


if __name__ == "__main__":
    main()
