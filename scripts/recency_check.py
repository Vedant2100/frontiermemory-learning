"""Recency check: does any task need newer corpus evidence to win over older evidence? Counts, ids and timestamps only.

For each of the 15 tasks: find its relevant v1.1 runs (prompt overlap with the task instruction, or the task's repository or
family named in the run's opening), order them by their recorded timestamps, and look for one kind of superseded information
that can be checked mechanically: a package that the task's own build files pin, mentioned with different versions in
different runs. Version values from the corpus are compared but never written out; only counts and match flags are.
Usage: python3 -I scripts/recency_check.py --data <dir with corpus/v1.1/inputs and tasks/frontier-memory> [--out results/recency-check.json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import corpus_coverage as cc  # noqa: E402
from build_corpus_evidence_v5 import Stats, load_items, outcome_of  # noqa: E402

FAMILIES = {"apex-brightpath": r"brightpath", "apex-eurogrid": r"eurogrid", "automationbench": r"automationbench",
            "awilix": r"awilix", "build-word2vec": r"word2vec", "cattrs": r"\bcattrs\b", "cookie-store": r"cookie.?store|cookiejar",
            "customer-delivery": r"customer.?delivery", "dapt": r"\bdapt\b|packets\.pcap", "enterpriseops": r"enterpriseops"}
STAMP = re.compile(r'"timestamp"\s*:\s*"(20\d\d-\d\d-\d\d[T ][0-9:.]+)')
PIN = re.compile(r"(?<![\w.-])([A-Za-z][A-Za-z0-9_.-]{1,40})\s*(?:==|@)\s*v?(\d+(?:\.\d+){1,3})\b")
OVERLAP = 0.3


def family(task: str) -> str | None:
    return next((k for k in FAMILIES if task.startswith(k)), None)


def task_pins(task_dir: Path) -> dict[str, str]:
    """Package pins in the task's own build and test files (public task data)."""
    pins = {}
    for f in list(task_dir.rglob("Dockerfile")) + list(task_dir.rglob("requirements*.txt")) + list(task_dir.rglob("test.sh")):
        for name, ver in PIN.findall(f.read_text(errors="ignore")):
            pins.setdefault(name.lower(), ver)
    return pins


def run_records(inputs: Path) -> list[dict]:
    out = []
    for path in sorted(inputs.iterdir()):
        raw = path.read_text(errors="ignore")
        _, items = load_items(path, Stats())
        stamps = sorted(STAMP.findall(raw))
        first = next((text for _, role, text in items if role == "user"), "")
        opening = " ".join(text for _, _, text in items[:4])[:6000]
        out.append({"id": path.stem, "verdict": outcome_of(items) or "NONE", "time": stamps[0][:19] if stamps else None,
                    "first_tokens": cc.tokens(first), "opening": opening, "pins": PIN.findall(raw)})
    return out


def analyse(data: Path) -> dict:
    cc.TASKS = data / "tasks/frontier-memory"
    wanted = cc.distinctive_instruction_tokens()
    runs = run_records(data / "corpus/v1.1/inputs")
    result = {}
    for task, toks in wanted.items():
        fam = family(task)
        rel = [r for r in runs if (toks and len(toks & r["first_tokens"]) / len(toks) >= OVERLAP)
               or (fam and re.search(FAMILIES[fam], r["opening"], re.I))]
        rel.sort(key=lambda r: (r["time"] is None, r["time"] or ""))
        pins = task_pins(cc.TASKS / task)
        conflicts = []
        for name, want in sorted(pins.items()):
            seen = defaultdict(set)  # version -> run ids, compared but never written out
            for r in rel:
                for n, v in r["pins"]:
                    if n.lower() == name:
                        seen[v].add(r["id"])
            if len(seen) < 2:
                continue
            timed = [r for r in rel if r["time"] and any(r["id"] in ids for ids in seen.values())]
            newest, oldest = (timed[-1], timed[0]) if timed else (None, None)
            def uses(r, v):
                return r is not None and r["id"] in seen.get(v, set())
            conflicts.append({"package": name, "distinct_versions_in_runs": len(seen),
                              "runs_mentioning": len(set().union(*seen.values())),
                              "task_pin_present_in_runs": want in seen,
                              "newest_run_matches_task_pin": uses(newest, want), "oldest_run_matches_task_pin": uses(oldest, want),
                              "newest_run": newest and {"id": newest["id"], "time": newest["time"], "verdict": newest["verdict"]},
                              "oldest_run": oldest and {"id": oldest["id"], "time": oldest["time"], "verdict": oldest["verdict"]}})
        seq = [r["verdict"] for r in rel if r["time"]]
        per_day = defaultdict(Counter)
        for r in rel:
            if r["time"]:
                per_day[r["time"][:10]][r["verdict"]] += 1
        latest = {v: max((r["time"] for r in rel if r["time"] and r["verdict"] == v), default=None) for v in ("PASS", "FAIL")}
        result[task] = {
            "per_day": {day: dict(c) for day, c in sorted(per_day.items())}, "latest_pass": latest["PASS"], "latest_fail": latest["FAIL"],
            "relevant_runs": len(rel), "timed": len(seq), "verdicts": dict(Counter(r["verdict"] for r in rel)),
            "time_range": [rel[0]["time"], next((r["time"] for r in reversed(rel) if r["time"]), None)] if rel else None,
            "distinct_days": len({r["time"][:10] for r in rel if r["time"]}),
            "pass_after_fail": any(a == "FAIL" and "PASS" in seq[i + 1:] for i, a in enumerate(seq)),
            "task_pinned_packages": len(pins), "version_conflicts": conflicts,
            "runs": [{"id": r["id"], "time": r["time"], "verdict": r["verdict"]} for r in rel],
        }
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=REPO / "results/recency-check.json")
    args = ap.parse_args()
    res = analyse(args.data)
    args.out.write_text(json.dumps(res, indent=1) + "\n")
    for task, v in res.items():
        c = v["version_conflicts"]
        print(f"{task[:44]:44s} runs={v['relevant_runs']:3d} timed={v['timed']:3d} days={v['distinct_days']:2d} {v['verdicts']} "
              f"pass_after_fail={v['pass_after_fail']} pins={v['task_pinned_packages']} conflicts={len(c)} "
              + " per-day PASS/all " + " ".join(f"{d[5:]}:{c.get('PASS', 0)}/{sum(c.values())}" for d, c in v["per_day"].items())
              + " ".join(f"[{x['package']}: {x['distinct_versions_in_runs']}v, newest_ok={x['newest_run_matches_task_pin']}, oldest_ok={x['oldest_run_matches_task_pin']}]" for x in c))


if __name__ == "__main__":
    main()
