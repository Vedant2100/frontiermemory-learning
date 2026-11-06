"""Check that every finished trial of an exploratory arm actually carried the arm (results/preregistration-arms.md).

Reads only saved trial files: Hermes's session file (agent/hermes-session.jsonl, whose first line holds the system prompt
the model received), the harness's agent/arm-report.json, the cue plugin's agent/fm-cue-metrics.json and result.json.
Skill names are matched only inside <available_skills>, because HM's MEMORY.md block also lists every skill's folder.
Prints counts and pass/fail only. Standard library only (guest system Python).

    python3 arm_check.py <task job dir> <arm>        (run from ~/official/frontiermemory, as the derived set script does)
"""

from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arm_logic  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
MEMORY_OF = {"readfirst": "jobs/fm-gen-run1", "scoped": "jobs/fm-gen-run1", "cue": "jobs/fm-gen-run1",
             "categorized": "jobs/fm-gen-run1", "cm": "jobs/fm-gen-run1", "km": "jobs/fm-gen-run1",
             "placebo": "jobs/fm-mem-placebo", "generator": "jobs/fm-gen-arm-generator"}
MEMORY_HEAD = "# Learned Hermes skills"  # first line of a Hermes /learn MEMORY.md (hermes_dream.export_skills)


def memory_dir(job: str) -> Path:
    if (Path(job) / "MEMORY.md").is_file():
        return Path(job)
    found = glob.glob(os.path.join(job, "*", "artifacts", "memory"))
    if len(found) != 1:
        raise SystemExit(f"expected one memory in {job}, found {len(found)}")
    return Path(found[0])


def session_prompt(trial: Path) -> str | None:
    p = trial / "agent" / "hermes-session.jsonl"
    if not p.is_file():
        return None
    with open(p, errors="replace") as f:
        return json.loads(f.readline()).get("system_prompt")


def load(p: Path) -> dict | None:
    return json.loads(p.read_text()) if p.is_file() else None


def check_trial(arm: str, trial: Path, mem: Path | None, emap: dict) -> list[str]:
    bad = []
    task = trial.name.split("__")[0]
    if arm in ("c0", "cm", "k0", "km"):
        has_memory = "memory_sha256" in (trial / "result.json").read_text()
        if has_memory != (arm in ("cm", "km")):
            bad.append("memory presence differs from the arm")
        return bad
    sp = session_prompt(trial)
    if sp is None:
        return ["no Hermes session file"]
    index = arm_logic.available_skills(sp)
    # Hermes lists a skill under its declared frontmatter name (agent/skill_utils.py resolve_skill_catalog: load_name)
    leaves = [s["name"] for s in arm_logic.skills(mem)] if mem else []
    in_index = sum(f"- {name}:" in index or f"- {name}\n" in index for name in leaves)
    report = load(trial / "agent" / "arm-report.json")
    if arm not in ("placebo", "generator") and (report is None or report.get("arm") != arm):
        return ["no arm report for this arm"]
    if arm in ("placebo", "generator") and MEMORY_HEAD not in sp:
        bad.append("memory block not shown")
    if arm == "placebo" and "Reading notes, part 1." not in sp:
        bad.append("placebo memory not the one shown")
    if arm == "readfirst":
        if arm_logic.READ_FIRST not in sp:
            bad.append("read-first sentence not in the system prompt")
        if MEMORY_HEAD not in sp:
            bad.append("memory block not shown")
    if arm == "scoped":
        want = min(arm_logic.K_SCOPED, len(leaves))
        if report.get("selected") != want or in_index != want:
            bad.append(f"scoped index has {in_index} memory skills, report {report.get('selected')}, expected {want}")
    if arm == "categorized":
        cats = {c: n for c, n in report.get("categories", {}).items() if n}
        if sum(cats.values()) != len(leaves) or in_index != len(leaves):
            bad.append("not every memory skill is indexed under a category")
        if any(f"{c}: {arm_logic.CATEGORIES[c][0]}" not in index for c in cats):
            bad.append("a category heading is missing")
    if arm == "cue":
        m = load(trial / "agent" / "fm-cue-metrics.json")
        if m is None or m.get("hook_calls", 0) < 1:
            bad.append("cue plugin never ran")
        elif m.get("skills") != len(leaves):
            bad.append("cue plugin saw a different number of skills")
        if in_index or MEMORY_HEAD in sp:
            bad.append("memory shown at start in the cue arm")
    if arm in ("raw", "evidence"):
        want = len(emap[task]) if arm == "evidence" else len(os.listdir("data/corpus/v1.1/inputs"))
        pointer = arm_logic.POINTER[arm].format(n=want, path=arm_logic.RECORDS_TARGET)
        if report.get("records") != want or (want and pointer not in sp) or (not want and "earlier agent work sessions" in sp):
            bad.append(f"records {report.get('records')}, expected {want}, or pointer missing")
        if MEMORY_HEAD in sp:
            bad.append("generated memory shown in a records arm")
    return bad


def main(argv: list[str]) -> int:
    job, arm = Path(argv[1]), argv[2]
    mem = memory_dir(MEMORY_OF[arm]) if arm in MEMORY_OF else None
    emap = json.loads((HERE / "evidence-runs.json").read_text())
    if arm == "generator":
        results = glob.glob(os.path.join(MEMORY_OF[arm], "*", "agent", "hermes-result.json"))
        req = [json.loads(open(p).read()).get("request", "") for p in results]
        if len(req) != 1 or not req[0].endswith(arm_logic.GENERATOR_ADDED_RULES):
            print("ARM_CHECK: FAIL generation did not use the generator arm's request")
            return 1
    trials = sorted(d for d in job.glob("*__*") if (d / "result.json").is_file())
    failed = 0
    for t in trials:
        bad = check_trial(arm, t, mem, emap)
        failed += bool(bad)
        print(f"{t.name}: {'ok' if not bad else 'FAIL: ' + '; '.join(bad)}")
    ok = bool(trials) and not failed
    print(f"ARM_CHECK: {'ok' if ok else 'FAIL'} arm={arm} trials={len(trials)} failed={failed}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
