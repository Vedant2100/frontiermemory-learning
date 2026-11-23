"""Where each failed requirement's information stopped, from earlier runs to the answer.

Inputs (private, read-only): checks.jsonl, access.jsonl, the per-task audit JSON
files, the outcome-blind notes labels, and causal/stages/<task>.json (corpus and
note-writer trace per requirement). Output: one JSON of counts, no raw text.
Usage: python3 stages.py PRIVATE_DIR BLIND_LABELS_JSON OUT_JSON

Stages of one failed trial-requirement, in the order information flows:
- in_task_missed: the prompt states it or the task's own files and tools give it;
  the agent had the information and still missed the requirement.
- no_memory_arm: control or placebo, information not in the task.
- raw_records_arm: evidence arm, information not in the task.
- blend_arm: blend arm, information not in the task (blend content not labelled blind).
- experience_missing: no earlier run in the corpus holds it.
- writer_never_saw: the corpus holds it; it never reached the writer's context.
- writer_saw_dropped: the writer saw it; the notes do not contain it.
- writer_saw_partial: the writer saw it; the notes contain part of it.
- harness_not_exposed: the notes contain it; the arm shows nothing and the agent did not find them.
- agent_did_not_open: the notes contain it and are listed; the agent did not open the relevant file.
- used_still_failed: the notes contain it and the agent opened the file or had it pasted in.
Flags carried alongside: unstated_spec (only the hidden checker knows the requirement).
"""
import json, os, sys, glob, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analysis import load, Data, MEMORY_OF, INPROMPT, ARMS

ORDER = ["experience_missing", "writer_never_saw", "writer_saw_dropped", "writer_saw_partial",
         "harness_not_exposed", "agent_did_not_open", "used_still_failed", "in_task_missed",
         "no_memory_arm", "raw_records_arm", "blend_arm"]
UPSTREAM_MAP = {"experience_missing": "experience_missing", "writer_never_saw": "writer_never_saw",
                "writer_saw_dropped": "writer_saw_dropped", "writer_saw_partial_kept": "writer_saw_partial",
                "in_notes": "in_notes"}


def load_trace(private):
    trace = {}
    for f in glob.glob(os.path.join(private, "causal", "stages", "*.json")):
        d = json.load(open(f))
        for q in d["requirements"]:
            trace[(d["task"][:32], q["req_id"])] = q
    return trace


def stage_of(t, r, q, access):
    if r["prompt"] in ("explicit", "derivable"):
        return "in_task_missed"
    arm = t["arm"]
    if arm in ("control", "placebo"):
        return "no_memory_arm"
    if arm == "evidence":
        return "raw_records_arm"
    if arm == "blend":
        return "blend_arm"
    gen = MEMORY_OF[arm]
    up = UPSTREAM_MAP.get((q or {}).get("stage", {}).get(gen), None)
    if up is None:
        return "untraced"
    if up != "in_notes":
        return up
    if arm in INPROMPT:
        return "used_still_failed"
    acc = access.get(t["trial"], {})
    f = r["memory_file"].get(gen)
    opened_relevant = bool(acc.get("opened")) and bool(f) and any(x.endswith(f) for x in acc.get("targets", []))
    if opened_relevant:
        return "used_still_failed"
    return "harness_not_exposed" if arm == "noneshown" else "agent_did_not_open"


def main(private, blind, out_path):
    checks, access, reqs, _ = load(private, blind)
    D = Data(checks, reqs)
    trace = load_trace(private)
    failed = [t for t in D.trials if t["reward"] < 1]
    inst = collections.defaultdict(list)
    req_counts = collections.Counter()
    req_counts_by_arm = collections.defaultdict(collections.Counter)
    unstated = collections.Counter()
    for t in failed:
        for r in reqs:
            if r["task"] != t["task"] or D.out[(t["trial"], r["key"])] != 0:
                continue
            q = trace.get((r["task"], r["id"]))
            s = stage_of(t, r, q, access)
            us = bool(q and str(q.get("unstated_spec", {}).get("value")).lower() == "true")
            inst[t["trial"]].append(s)
            req_counts[s] += 1
            req_counts_by_arm[t["arm"]][s] += 1
            if us:
                unstated[s] += 1
    upstream_all = {g: collections.Counter() for g in ("run1", "run3", "run4")}
    corpus_all = collections.Counter()
    for t in failed:
        for r in reqs:
            if r["task"] != t["task"] or D.out[(t["trial"], r["key"])] != 0:
                continue
            q = trace.get((r["task"], r["id"])) or {}
            corpus_all[(q.get("corpus") or {}).get("status", "untraced")] += 1
            for g in upstream_all:
                upstream_all[g][UPSTREAM_MAP.get((q.get("stage") or {}).get(g), "untraced")] += 1
    req_level = []
    for r in reqs:
        q = trace.get((r["task"], r["id"])) or {}
        nfail = sum(1 for t in failed if t["task"] == r["task"] and D.out[(t["trial"], r["key"])] == 0)
        req_level.append({"key": r["key"], "prompt": r["prompt"], "failed_trials": nfail,
                          "corpus": (q.get("corpus") or {}).get("status"), "corpus_kinds": (q.get("corpus") or {}).get("kinds"),
                          "stage": q.get("stage"), "unstated_spec": (q.get("unstated_spec") or {}).get("value")})
    any_stage = collections.Counter()
    only_stage = collections.Counter()
    for t in failed:
        ss = set(inst[t["trial"]])
        for s in ss:
            any_stage[s] += 1
        if len(ss) == 1:
            only_stage[next(iter(ss))] += 1
    def waterfall(order):
        rem = {t["trial"] for t in failed}
        rows = []
        for s in order:
            hit = {tr for tr in rem if s in inst[tr]}
            rows.append({"stage": s, "trials": len(hit)})
            rem -= hit
        rows.append({"stage": "other_or_none", "trials": len(rem)})
        return rows
    present = [s for s in ORDER if s in req_counts] + sorted(s for s in req_counts if s not in ORDER)
    out = {
        "failed_trials": len(failed),
        "failed_trial_requirements": sum(req_counts.values()),
        "trial_requirements_by_stage": {s: req_counts[s] for s in present},
        "of_which_unstated_spec": {s: unstated[s] for s in present if unstated[s]},
        "trial_requirements_by_arm_and_stage": {a: {s: req_counts_by_arm[a][s] for s in present if req_counts_by_arm[a][s]} for a in ARMS},
        "trials_with_any_failure_at_stage": {s: any_stage[s] for s in present},
        "trials_whose_failures_are_all_one_stage": {s: only_stage[s] for s in present if only_stage[s]},
        "trials_with_mixed_stages": sum(1 for t in failed if len(set(inst[t["trial"]])) > 1),
        "waterfall_upstream_first": waterfall(present),
        "waterfall_downstream_first": waterfall(list(reversed(present))),
        "all_failed_trial_requirements_by_corpus_status": dict(corpus_all),
        "all_failed_trial_requirements_by_upstream_stage_per_generation": {g: dict(c) for g, c in upstream_all.items()},
        "requirements": req_level,
        "untraced_requirements":sorted({f"{r['task']}:{r['id']}" for r in reqs if (r["task"], r["id"]) not in trace}),
    }
    json.dump(out, open(out_path, "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "trial_requirements_by_arm_and_stage"}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
