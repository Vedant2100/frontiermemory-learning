"""Exploratory arms (results/preregistration-arms.md): per-task comparisons with the preregistered study's own test.

Every comparison is exploratory and is labelled so. Each uses scripts/analyze_official.py's one-sided exact paired sign-flip
over task-level pass-rate differences and its 95% interval by test inversion. Matched comparators:
  delivery and content arms (same memory as HM run 1 or derived from it) -> HM run 1, and the no-memory control (A0);
  records arms (raw, evidence) and the generator -> A0, and HM run 1 for reference;
  Codex / Claude Code -> their own no-memory arm (CM vs C0, KM vs K0); C0 and K0 vs A0 are descriptive only (harness, no memory).
Dose (post hoc, descriptive, no test): pass rate by how much memory the agent saw at start, ordered E-none = cue (none) <
scoped (top-3 index) < HM run 1 = categorized (full index) < read-first (index + nudge) < E-all (all files).
Recency: the probe results (current / stale / both / neither per injected fact) by variant.

    python3 -I scripts/analyze_arms.py --dir results/official [--self-test]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_official import EXPECTED_ATTEMPTS, N_TASKS, compare, read_set, tally  # noqa: E402

CONTROL, HM1 = "fm-tasks-control", "fm-tasks-run1"
ARM = "fm-tasks-arm-{}"
VS_HM_AND_A0 = ("placebo", "readfirst", "scoped", "cue", "categorized")
VS_A0 = ("raw", "evidence", "generator")
EXPOSURE = {"exposure-none": "fm-tasks-exposure-none", "exposure-all": "fm-tasks-exposure-all"}
WITHIN = {"codex": ("c0", "cm"), "claude-code": ("k0", "km")}
DOSE = [("none shown at start", ["exposure-none", "cue"]), ("top-3 skills indexed", ["scoped"]),
        ("full index (HM)", ["hm-run1", "categorized"]), ("index + read-first", ["readfirst"]), ("all files", ["exposure-all"])]
NO_MEMORY = {"raw", "evidence", "c0", "k0"}


def checks(name: str, rows: list[dict], memory: bool) -> list[str]:
    flags = []
    if bad := [r for r in rows if not r.get("valid")]:
        flags.append(f"{name}: {len(bad)} trial(s) with no reward")
    if failed := [r for r in rows if r.get("judge_status") not in (None, "completed")]:
        flags.append(f"{name}: {len(failed)} trial(s) where the LLM judge failed: regrade them")
    counts = tally(rows)
    if len(counts) != N_TASKS or any(c[1] != EXPECTED_ATTEMPTS for c in counts.values()):
        flags.append(f"{name}: not {N_TASKS} tasks x {EXPECTED_ATTEMPTS} attempts")
    digests = {r.get("memory_sha256") for r in rows}
    if memory and (None in digests or len(digests) != 1):
        flags.append(f"{name}: expected one memory digest on every trial")
    if not memory and digests - {None}:
        flags.append(f"{name}: a no-memory arm trial has a memory digest")
    return flags


def rate(rows: list[dict]) -> float:
    valid = [r for r in rows if r.get("valid")]
    return sum(bool(r.get("passed")) for r in valid) / len(valid) if valid else float("nan")


def labelled(comp: dict, label: str) -> dict:
    return {"label": f"exploratory: {label}", **{k: comp[k] for k in ("tasks", "mean_diff", "ci95", "p_one_sided",
                                                                       "tasks_up", "tasks_down")}}


def recency(res: Path) -> dict:
    out = {}
    for f in sorted(res.glob("recency-probe-arm-recency-*.txt")):
        m = re.search(r"RECENCY_PROBE (\{.*\})", f.read_text())
        if m:
            r = json.loads(m.group(1))
            out[r["variant"]] = {"facts": r["facts"], "outcomes": r["outcomes"]}
    return out


def analyse(sets: dict[str, list[dict]], res: Path | None = None) -> dict:
    out: dict = {"flags": [], "comparisons": {}, "pass_rates": {}}
    have = lambda n: n in sets  # noqa: E731
    named = {**{a: ARM.format(a) for a in (*VS_HM_AND_A0, *VS_A0, "c0", "cm", "k0", "km")}, **EXPOSURE, "hm-run1": HM1,
             "control": CONTROL}
    for arm, job in named.items():
        if have(job):
            out["pass_rates"][arm] = rate(sets[job])
            if arm not in ("hm-run1", "control"):
                out["flags"] += checks(arm, sets[job], memory=arm not in NO_MEMORY)
    tables = {k: tally(v) for k, v in sets.items()}

    def comp(a: str, b: str, label: str):
        if have(a) and have(b):
            tasks = sorted(set(tables[a]) & set(tables[b]))
            if len(tasks) == N_TASKS:
                out["comparisons"][label] = labelled(compare(tables[b], tables[a], tasks), label)
            else:
                out["flags"].append(f"{label}: only {len(tasks)} shared tasks; not compared")

    for arm in (*VS_HM_AND_A0, *EXPOSURE):
        job = named[arm]
        comp(job, HM1, f"{arm} vs HM run 1 (same memory)")
        comp(job, CONTROL, f"{arm} vs no memory (A0)")
    for arm in VS_A0:
        comp(named[arm], CONTROL, f"{arm} vs no memory (A0)")
        comp(named[arm], HM1, f"{arm} vs HM run 1 (reference)")
    for harness, (zero, mem) in WITHIN.items():
        comp(named[mem], named[zero], f"{harness}: memory vs no memory (within harness)")
        if have(named[zero]) and have(CONTROL):
            out["comparisons"][f"{harness} no memory vs Hermes no memory"] = {
                "label": "descriptive only: harness difference, no test",
                "pass_rate_diff": rate(sets[named[zero]]) - rate(sets[CONTROL])}
    out["dose_post_hoc"] = [{"exposure": level, "arms": [a for a in arms if a in out["pass_rates"]],
                             "pass_rate": [round(out["pass_rates"][a], 3) for a in arms if a in out["pass_rates"]]}
                            for level, arms in DOSE]
    if res is not None:
        out["recency"] = recency(res)
    return out


def self_test() -> None:
    tasks = [f"t{i:02d}" for i in range(N_TASKS)]

    def rows(passes: dict, digest):
        return [{"task": f"letta-ai/{t}", "valid": True, "passed": k < passes.get(t, 0), "memory_sha256": digest}
                for t in tasks for k in range(EXPECTED_ATTEMPTS)]
    sets = {CONTROL: rows({}, None), HM1: rows({"t00": 1}, "a"), ARM.format("placebo"): rows({}, "p"),
            ARM.format("readfirst"): rows({t: 3 for t in tasks[:6]}, "a"), ARM.format("c0"): rows({}, None),
            ARM.format("cm"): rows({"t01": 2}, "a")}
    out = analyse(sets)
    rf = out["comparisons"]["readfirst vs HM run 1 (same memory)"]
    assert rf["tasks_up"] == 6 and rf["tasks_down"] == 0 and abs(rf["p_one_sided"] - 1 / 64) < 1e-12, rf  # 6 up, 9 tied
    assert out["comparisons"]["placebo vs no memory (A0)"]["mean_diff"] == 0
    assert out["comparisons"]["codex: memory vs no memory (within harness)"]["tasks_up"] == 1
    assert not out["flags"], out["flags"]
    bad = analyse({**sets, ARM.format("raw"): rows({}, "x")})
    assert any("no-memory arm" in f for f in bad["flags"])
    print("self-test ok")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", type=Path, default=Path("results/official"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    sets = {p.name[len("summary-"):-len(".jsonl")]: read_set(p) for p in sorted(args.dir.glob("summary-fm-tasks-*.jsonl"))}
    print(json.dumps(analyse(sets, args.dir), indent=1))


if __name__ == "__main__":
    main()
