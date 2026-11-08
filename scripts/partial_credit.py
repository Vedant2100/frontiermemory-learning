"""Hidden-test partial credit per trial (preregistered secondary outcome: "official partial credit where the verifier
reports it", results/preregistration-v2.md). Counts only, never task or memory text. D131.

Two modes.
  extract (stdlib only; runs in the guest VM, read-only, as root so it can read the trial folders):
      sudo python3 - extract /home/fm/official/frontiermemory/jobs fm-tasks-control fm-tasks-run1 ...  < partial_credit.py
    prints one JSON line per trial: job, trial, strict (the verifier's reward), partial (0..1), and the parts used.
  analyze (host): python3 -I scripts/partial_credit.py analyze [--dir results/official]
    reads results/official/partial-credit-<job>.jsonl plus summary-<job>.jsonl (for the task name) and runs the
    preregistered paired sign-flip over the 15 tasks (scripts/analyze_official.py) on per-task mean partial credit.

Per-trial value in [0, 1], by task family, from what each verifier writes:
  APEX (3 tasks)            reward.json "reward": the fraction of rubric checks passed (the grader's own score)
  AutomationBench (3)       verifier.json "partial_credit": assertions passed / total
  EnterpriseOps (2)         verifier.json "pass_fraction": checks passed / total
  cattrs, customer delivery reward.json "partial": hidden tests passed / total (the official field)
  DAPT                      ctrf.json: tests passed / tests
  Word2Vec                  pytest summary in test-stdout.txt: passed / (passed + failed)
  cookie store              mean of (a) new-test pass fraction, from the pytest run after "Running new tests", and
                            (b) preference gates passed / 4 (user-preference.json)
  awilix (2)                mean of (a) new-test pass fraction from the jest run after "Running new tests" (0 if that
                            suite did not run), and (b) the preference test, user-preference-ctrf.json passed / tests
Check built in: for every trial, partial == 1 exactly when the trial's strict reward is 1 (except Eurogrid, whose
reward tops out at 0.8333). Any violation is reported and the analysis refuses to run.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _j(path):
    with open(path) as f:
        return json.load(f)


def _txt(path):
    return ANSI.sub("", open(path, errors="replace").read()) if os.path.exists(path) else ""


def _pytest_fraction(text: str):
    """passed / (passed + failed) from the LAST pytest summary line in text; None if there is none."""
    lines = [l for l in text.splitlines() if re.search(r"\d+ (passed|failed)", l) and " in " in l]
    if not lines:  # collection error (e.g. the agent wrote no solution file): no hidden test could pass
        return 0.0 if any(re.search(r"\d+ errors? in ", l) for l in text.splitlines()) else None
    p = sum(int(x) for x in re.findall(r"(\d+) passed", lines[-1]))
    f = sum(int(x) for x in re.findall(r"(\d+) failed", lines[-1]))
    return None if p + f == 0 else p / (p + f)


def _after_new_tests(text: str) -> str:
    i = text.find("Running new tests")
    return text[i:] if i >= 0 else ""


def _jest_fraction(text: str):
    """passed / total from the last jest "Tests:" line; 0.0 if the suite never ran (no such line or 0 total)."""
    lines = re.findall(r"^Tests:\s+(.*)$", text, re.M)
    if not lines:
        return 0.0
    tot = re.search(r"(\d+) total", lines[-1])
    p = re.search(r"(\d+) passed", lines[-1])
    if not tot or int(tot.group(1)) == 0:
        return 0.0
    return (int(p.group(1)) if p else 0) / int(tot.group(1))


def _ctrf(path):
    s = _j(path)["results"]["summary"]
    return s["passed"] / s["tests"] if s.get("tests") else None


def strict_reward(v: str):
    for name in ("reward.txt",):
        p = os.path.join(v, name)
        if os.path.exists(p) and open(p).read().strip():
            return float(open(p).read().strip())
    p = os.path.join(v, "reward.json")
    return float(_j(p)["reward"]) if os.path.exists(p) else None


def partial_for(task_dir: str):
    v = os.path.join(task_dir, "verifier")
    key = os.path.basename(task_dir.rstrip("/")).split("__")[0]
    parts = {}
    if key.startswith("apex-"):
        val = float(_j(os.path.join(v, "reward.json"))["reward"])
    elif key.startswith("automationbench-"):
        val = float(_j(os.path.join(v, "verifier.json"))["partial_credit"])
    elif key.startswith("enterpriseops-"):
        val = float(_j(os.path.join(v, "verifier.json"))["pass_fraction"])
    elif key.startswith(("cattrs-", "customer-delivery")):
        val = float(_j(os.path.join(v, "reward.json"))["partial"])
    elif key.startswith("dapt-"):
        val = _ctrf(os.path.join(v, "ctrf.json"))
    elif key.startswith("build-word2vec"):
        val = _pytest_fraction(_txt(os.path.join(v, "test-stdout.txt")))
    elif key.startswith("cookie-store"):
        a = _pytest_fraction(_after_new_tests(_txt(os.path.join(v, "test-stdout.txt"))))
        gates = _j(os.path.join(v, "user-preference.json"))["gates"]
        b = sum(bool(g["passed"]) for g in gates) / len(gates) if gates else None
        parts = {"tests": a, "gates": b}
        val = None if a is None or b is None else (a + b) / 2
    elif key.startswith("awilix-"):
        a = _jest_fraction(_after_new_tests(_txt(os.path.join(v, "test-stdout.txt"))))
        b = _ctrf(os.path.join(v, "user-preference-ctrf.json"))
        parts = {"tests": a, "preference": b}
        val = None if b is None else (a + b) / 2
    else:
        raise ValueError(f"unknown task family {key}")
    return val, parts


def extract(root: str, jobs: list[str]) -> None:
    for job in jobs:
        for t in sorted(glob.glob(os.path.join(root, job, "*__*/"))):
            if not os.path.isdir(os.path.join(t, "verifier")):
                continue
            name = os.path.basename(t.rstrip("/"))
            try:
                partial, parts = partial_for(t)
                err = None
            except Exception as e:  # reported, never guessed
                partial, parts, err = None, {}, f"{type(e).__name__}: {e}"
            print(json.dumps({"job": job, "trial": name, "strict": strict_reward(os.path.join(t, "verifier")),
                              "partial": partial, "parts": parts, "error": err}))


def analyze(d: str) -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    import analyze_official as ao  # noqa: E402

    rows = {}
    problems = []
    for p in sorted(glob.glob(os.path.join(d, "partial-credit-*.jsonl"))):
        job = os.path.basename(p)[len("partial-credit-"):-len(".jsonl")]
        summary = {r["trial"]: r for r in map(json.loads, open(os.path.join(d, f"summary-{job}.jsonl")))}
        rows[job] = []
        for r in map(json.loads, open(p)):
            if r["trial"] not in summary:
                continue  # e.g. a trial set aside after an incident
            task = ao.task_name(summary[r["trial"]])
            if r["partial"] is None or r["error"]:
                problems.append((job, r["trial"], "no partial credit", r["error"]))
                continue
            strict_one = bool(summary[r["trial"]].get("passed"))
            if strict_one != (abs(r["partial"] - 1.0) < 1e-9):
                problems.append((job, r["trial"], f"strict passed={strict_one} but partial={r['partial']:.3f}", r["parts"]))
            rows[job].append((task, r["partial"]))
    if problems:
        print(json.dumps({"CHECK_FAILED": len(problems), "first": problems[:8]}, indent=1))
        sys.exit(1)

    def per_task(jobs):
        acc: dict[str, list[float]] = {}
        for j in jobs:
            for task, val in rows.get(j, []):
                s = acc.setdefault(task, [0.0, 0])
                s[0] += val
                s[1] += 1
        return acc

    tasks = sorted(per_task(["fm-tasks-control"]))
    ctrl = per_task(["fm-tasks-control"])
    mem = per_task(["fm-tasks-run1", "fm-tasks-run3", "fm-tasks-run4"])
    out = {"trials_per_set": {j: len(t) for j, t in rows.items()},
           "mean_partial": {name: round(sum(v[0] for v in acc.values()) / sum(v[1] for v in acc.values()), 4)
                            for name, acc in (("control", ctrl), ("memory_runs_1_3_4", mem),
                                              ("placebo", per_task(["fm-tasks-arm-placebo"])))},
           "memory_vs_control": ao.compare(ctrl, mem, tasks)}
    if "fm-tasks-arm-placebo" in rows:
        out["placebo_vs_control"] = ao.compare(ctrl, per_task(["fm-tasks-arm-placebo"]), tasks)
        out["placebo_vs_run1"] = ao.compare(per_task(["fm-tasks-run1"]), per_task(["fm-tasks-arm-placebo"]), tasks)
    for arm in ("fm-tasks-arm-readfirst",):  # further exploratory arms are added here as they finish
        if arm in rows:
            out[f"{arm}_vs_control"] = ao.compare(ctrl, per_task([arm]), tasks)
            out[f"{arm}_vs_run1"] = ao.compare(per_task(["fm-tasks-run1"]), per_task([arm]), tasks)
            out["mean_partial"][arm] = round(sum(v[0] for v in per_task([arm]).values()) / sum(v[1] for v in per_task([arm]).values()), 4)
    for j in ("fm-tasks-run1", "fm-tasks-run3", "fm-tasks-run4"):
        out[f"{j}_vs_control"] = {k: v for k, v in ao.compare(ctrl, per_task([j]), tasks).items() if k != "per_task"}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "extract":
        extract(sys.argv[2], sys.argv[3:])
    elif len(sys.argv) >= 2 and sys.argv[1] == "analyze":
        analyze(sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else "results/official")
    else:
        sys.exit(__doc__)
