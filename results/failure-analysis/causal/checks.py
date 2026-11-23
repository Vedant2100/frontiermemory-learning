"""Build a check-level outcome table for every counted trial.

Reads the private trial directories read-only and writes checks.jsonl:
one row per trial with the pass/fail state of every verifier check.
Usage: python3 checks.py JOBS_ROOT OUT.jsonl
"""
import json, re, sys, glob, os

ANSI = re.compile(r"\x1b\[[0-9;]*m")
ARMS = {
    "oracle": "oracle-all",
    "control": "fm-tasks-control",
    "run1": "fm-tasks-run1",
    "run3": "fm-tasks-run3",
    "run4": "fm-tasks-run4",
    "placebo": "fm-tasks-arm-placebo",
    "readfirst": "fm-tasks-arm-readfirst",
    "allshown": "fm-tasks-exposure-all",
    "noneshown": "fm-tasks-exposure-none",
    "evidence": "fm-tasks-arm-evidence",
    "blend": "fm-tasks-arm-blend",
}


def read(p):
    try:
        return ANSI.sub("", open(p, errors="replace").read())
    except OSError:
        return None


def pytest_checks(text):
    out = {}
    for m in re.finditer(r"^(\S+::\S+)[ \t]+(PASSED|FAILED|ERROR|SKIPPED)\b", text, re.M):
        name = m.group(1).split("tests/")[-1]
        out[name] = 1 if m.group(2) == "PASSED" else 0
    return out


def bracket_checks(text):
    out = {}
    for m in re.finditer(r"^\[(PASS|FAIL)\] (.+?)(?::\s*actual=.*)?$", text, re.M):
        out[m.group(2).strip()] = 1 if m.group(1) == "PASS" else 0
    return out


def jest_checks(text):
    out = {}
    for m in re.finditer(r"^\s*([✓✕○])\s+(.+?)(?:\s+\(\d+ ms\))?$", text, re.M):
        if m.group(1) == "○":
            continue
        out["fn:" + m.group(2).strip()] = 1 if m.group(1) == "✓" else 0
    return out


def trial_checks(v):
    checks, kind, note = {}, None, ""
    gd = os.path.join(v, "grade_details.json")
    if os.path.exists(gd):
        kind = "judge"
        d = json.load(open(gd))
        for r in d.get("verifier_results", []):
            checks[r["verifier_id"]] = 1 if (r.get("score") or 0) >= 1 else 0
        return kind, checks, note
    out = read(os.path.join(v, "test-stdout.txt")) or ""
    b = bracket_checks(out)
    if b:
        return "assertions", b, note
    up = os.path.join(v, "user-preference-ctrf.json")
    upj = os.path.join(v, "user-preference.json")
    if os.path.exists(up) or os.path.exists(upj):
        kind = "functional+preference"
        checks.update(jest_checks(out))
        checks.update({"fn:" + k: val for k, val in pytest_checks(out).items()})
        fr = read(os.path.join(v, "functional-reward.txt"))
        if fr is not None:
            checks["functional(all)"] = 1 if fr.strip().startswith("1") else 0
        if os.path.exists(up):
            for t in json.load(open(up))["results"]["tests"]:
                checks["pref:" + t["name"]] = 1 if t["status"] == "passed" else 0
        if os.path.exists(upj):
            for g in json.load(open(upj)).get("gates", []):
                checks["pref:" + g["id"]] = 1 if g.get("passed") else 0
        return kind, checks, note
    p = pytest_checks(out)
    ct = os.path.join(v, "ctrf.json")
    if os.path.exists(ct):
        tests = json.load(open(ct))["results"]["tests"]
        if len(tests) > len(p):
            p = {}
    if p:
        return "pytest", p, note
    if os.path.exists(ct):
        for t in json.load(open(ct))["results"]["tests"]:
            checks[t["name"]] = 1 if t["status"] == "passed" else 0
        return "ctrf", checks, note
    if "error during collection" in out or "Interrupted" in out:
        return "collection-error", {"test_outputs.py::test_solution_exists": 0}, "verifier could not load the solution; other tests never ran"
    return "unknown", {}, "no parsable check output"


def main(root, outp):
    rows = []
    for arm, job in ARMS.items():
        for td in sorted(glob.glob(os.path.join(root, job, "*__*"))):
            if not os.path.isdir(td):
                continue
            rj = os.path.join(td, "result.json")
            if not os.path.exists(rj):
                continue
            res = json.load(open(rj))
            vr = (res.get("verifier_result") or {}).get("rewards") or {}
            reward = vr.get("reward")
            if reward is None:
                t = read(os.path.join(td, "verifier", "reward.txt"))
                reward = float(t.strip()) if t and t.strip() else None
            kind, checks, note = trial_checks(os.path.join(td, "verifier"))
            name = os.path.basename(td)
            rows.append({
                "arm": arm, "trial": name, "task": name.rsplit("__", 1)[0],
                "reward": reward, "kind": kind, "n_checks": len(checks),
                "n_failed": sum(1 for x in checks.values() if not x),
                "checks": checks, "note": note,
                "exception": (res.get("exception_info") or {}).get("exception_type"),
            })
    universe = {}
    for r in rows:
        universe.setdefault(r["task"], set()).update(r["checks"])
    for r in rows:
        default = 1 if r["kind"] == "assertions" else 0
        for c in universe[r["task"]]:
            if c not in r["checks"]:
                r["checks"][c] = default
                r.setdefault("filled", []).append(c)
        r["n_checks"] = len(r["checks"])
        r["n_failed"] = sum(1 for x in r["checks"].values() if not x)
    with open(outp, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(len(rows), "rows")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
