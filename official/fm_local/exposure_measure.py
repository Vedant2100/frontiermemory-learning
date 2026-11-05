"""Measure, from saved trials, how much of a memory the task agent's system prompt actually carried. Counts only, never text.

For each trial, Hermes's session file (agent/hermes-session.jsonl) holds the system prompt. A memory file counts as shown
when a probe from it (its longest line, up to 80 characters, at least 20) appears in that prompt; a skill counts as indexed
when its folder name appears there.

    python3 exposure_measure.py <task job dir> <memory-generation job dir> [none|all|hm]

With an arm, the exit status checks it: none needs 0 files shown and 0 skills indexed; all needs every file shown;
hm needs MEMORY.md shown. Without one, it only reports.
"""

import glob
import json
import os
import sys


def probes(memory_dir):
    out = {}
    for p in sorted(glob.glob(os.path.join(memory_dir, "**", "*"), recursive=True)):
        if not os.path.isfile(p):
            continue
        lines = [l.strip() for l in open(p, encoding="utf-8", errors="replace")]
        best = max(lines, key=len, default="")[:80]
        if len(best) >= 20:
            out[os.path.relpath(p, memory_dir)] = best
    return out


def skill_names(memory_dir):
    return sorted({os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(memory_dir, "**", "SKILL.md"), recursive=True)})


def system_prompt(trial_dir):
    p = os.path.join(trial_dir, "agent", "hermes-session.jsonl")
    if not os.path.exists(p):
        return None
    with open(p, errors="replace") as f:
        return json.loads(f.readline()).get("system_prompt")


def main():
    task_job, gen_job = sys.argv[1], sys.argv[2]
    arm = sys.argv[3] if len(sys.argv) > 3 else None
    mems = glob.glob(os.path.join(gen_job, "*", "artifacts", "memory"))
    if len(mems) != 1:
        sys.exit(f"expected one memory in {gen_job}, found {len(mems)}")
    pr, skills = probes(mems[0]), skill_names(mems[0])
    ok = True
    trials = sorted(d for d in glob.glob(os.path.join(task_job, "*__*")) if os.path.isfile(os.path.join(d, "result.json")))  # finished
    for t in trials:
        sp = system_prompt(t)
        if sp is None:
            print(f"{os.path.basename(t)}: no session file")
            ok = False
            continue
        shown = [k for k, v in pr.items() if v in sp]
        indexed = sum(n in sp for n in skills)
        md = "MEMORY.md" in shown
        print(f"{os.path.basename(t)}: system prompt {len(sp)} chars; files shown {len(shown)} of {len(pr)} (MEMORY.md {md}); "
              f"skills indexed {indexed} of {len(skills)}")
        if arm == "none" and (shown or indexed):
            ok = False
        if arm == "all" and len(shown) != len(pr):
            ok = False
        if arm == "hm" and not md:
            ok = False
    if not trials:
        print("no trials")
        ok = False
    print("EXPOSURE_MEASURE:", "ok" if ok else "FAIL", f"(arm {arm})" if arm else "(report only)")
    sys.exit(0 if ok or not arm else 1)


if __name__ == "__main__":
    main()
