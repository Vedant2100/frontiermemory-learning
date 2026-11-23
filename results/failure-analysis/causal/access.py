"""Extract memory-access events from every counted trial trajectory.

A memory access is a skill_view call, a skills_list call, a memory tool call,
or any file tool or shell command that names a staged memory or record path.
Usage: python3 access.py JOBS_ROOT OUT.jsonl
"""
import json, re, sys, glob, os

ARMS = {
    "control": "fm-tasks-control", "run1": "fm-tasks-run1", "run3": "fm-tasks-run3",
    "run4": "fm-tasks-run4", "placebo": "fm-tasks-arm-placebo",
    "readfirst": "fm-tasks-arm-readfirst", "allshown": "fm-tasks-exposure-all",
    "noneshown": "fm-tasks-exposure-none", "evidence": "fm-tasks-arm-evidence",
    "blend": "fm-tasks-arm-blend",
}
MEM_PATH = re.compile(r"(/tmp/hermes/memories[\w.\-/]*|/tmp/hermes/skills[\w.\-/]*|/root/\.hermes/(?:skills|memories)[\w.\-/]*|~/\.hermes/(?:skills|memories)[\w.\-/]*|/tmp/hermes/records[\w.\-/]*)")


STAGED = ("eval-task-families", "task-contract-playbook", "task-playbook", "note-01", "MEMORY.md", "/records/")


def is_content(e):
    t = e["target"]
    if e["kind"] == "memory_tool":
        return False
    if not any(k in t for k in STAGED):
        return False
    return e["kind"] == "skill_view" or bool(re.search(r"\.(md|json|jsonl|txt|log|py)$", t))


def events(traj):
    out = []
    for s in traj.get("steps", []):
        for tc in s.get("tool_calls") or []:
            fn = tc.get("function_name")
            args = tc.get("arguments") or {}
            if fn == "skill_view":
                f = args.get("file_path") or "SKILL.md"
                out.append({"step": s["step_id"], "kind": "skill_view", "target": f"{args.get('name')}/{f}"})
            elif fn == "skills_list":
                out.append({"step": s["step_id"], "kind": "skills_list", "target": "index"})
            elif fn == "memory":
                out.append({"step": s["step_id"], "kind": "memory_tool", "target": json.dumps(args)[:120]})
            else:
                for m in set(MEM_PATH.findall(json.dumps(args))):
                    kind = "records" if "/records" in m else "memory_path"
                    out.append({"step": s["step_id"], "kind": kind, "target": m.rstrip("/")})
    return out


def main(root, outp):
    n = 0
    with open(outp, "w") as f:
        for arm, job in ARMS.items():
            for tp in sorted(glob.glob(os.path.join(root, job, "*__*", "agent", "trajectory.json"))):
                trial = tp.split(os.sep)[-3]
                ev = events(json.load(open(tp)))
                content = [e for e in ev if is_content(e)]
                f.write(json.dumps({
                    "arm": arm, "trial": trial, "task": trial.rsplit("__", 1)[0],
                    "opened": bool(content), "first_open_step": min((e["step"] for e in content), default=None),
                    "listed_index": any(e["kind"] == "skills_list" for e in ev),
                    "probed": any(e["kind"] in ("memory_path", "records") for e in ev),
                    "targets": sorted({e["target"] for e in content}), "events": ev,
                }) + "\n")
                n += 1
    print(n, "trials")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
