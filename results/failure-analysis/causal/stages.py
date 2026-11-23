"""Where each failed requirement's information stopped, from earlier runs to the answer.

Inputs (private, read-only): checks.jsonl, access.jsonl, the per-task audit JSON
files, the outcome-blind notes labels, causal/stages/<task>.json (corpus and
note-writer trace per requirement) and, optionally, outcome-blind prompt labels.
Output: one JSON of counts, no raw text.
Usage: python3 stages.py PRIVATE_DIR BLIND_NOTES_LABELS OUT_JSON [BLIND_PROMPT_LABELS]

Stages of one failed trial-requirement, in the order information flows:
- in_task_missed: the prompt states it or the task's own files and tools give it;
  the agent had access to the information and still missed the requirement.
- no_memory_arm, raw_records_arm, blend_arm: arms without blind-labelled generated
  notes, information not in the task.
- experience_missing: no earlier run in the corpus holds it.
- writer_never_saw: the corpus holds it; it never reached the writer's context.
- writer_misled: the notes carry a rule the outcome-blind labeller flagged as
  misleading for this requirement.
- writer_saw_dropped: the writer saw it; the notes do not contain it.
- writer_saw_partial: the writer saw it; the notes contain part of it.
- not_shown_by_design: the notes contain it; the none-shown arm shows nothing and
  the agent did not find them.
- not_opened: the notes contain it and are listed; the agent did not open the
  relevant file. This includes the harness's index design.
- used_still_failed: the notes contain it fully and the agent opened the file or
  had it pasted in.
A prompt mode decides "in the task": "auditor" uses the auditors' labels
(explicit or derivable), "explicit_only" counts only explicit, "blind" uses the
outcome-blind prompt labels (explicit or derivable), and "blind_strict" also
drops blind labels of low confidence and two the reviewer judged too generous.
"""
import json, os, sys, glob, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analysis import load, Data, MEMORY_OF, INPROMPT, ARMS, level

NOTES_ARMS = [a for a in MEMORY_OF if a != "blend"]
UPSTREAM = ["experience_missing", "writer_never_saw", "writer_misled", "writer_saw_dropped", "writer_saw_partial"]
DOWNSTREAM = ["not_shown_by_design", "not_opened", "used_still_failed"]
ARM_STAGES = ["no_memory_arm", "raw_records_arm", "blend_arm"]
WRITER_FIRST = UPSTREAM + DOWNSTREAM + ["in_task_missed"] + ARM_STAGES
IN_TASK_FIRST = ["in_task_missed"] + UPSTREAM + DOWNSTREAM + ARM_STAGES
TRACE_MAP = {"experience_missing": "experience_missing", "writer_never_saw": "writer_never_saw",
             "writer_saw_dropped": "writer_saw_dropped", "writer_saw_partial_kept": "writer_saw_partial",
             "in_notes": "in_notes"}


def parse(x):
    if isinstance(x, str):
        try:
            import ast
            return ast.literal_eval(x)
        except Exception:
            return x
    return x


def load_trace(private):
    trace = {}
    for f in glob.glob(os.path.join(private, "causal", "stages", "*.json")):
        d = json.load(open(f))
        for q in d["requirements"]:
            trace[(d["task"][:32], q["req_id"])] = q
    return trace


def load_misleading(blind_path):
    out = {}
    for b in json.load(open(blind_path)):
        m = parse(b.get("misleading")) or {}
        out[(b["task"][:32], b["req_id"])] = {g: bool(m.get(g)) for g in ("run1", "run3", "run4")} if isinstance(m, dict) else {}
    return out


def load_blind_prompt(path):
    if not path:
        return {}
    out = {}
    for f in sorted(glob.glob(path)):
        for b in json.load(open(f)):
            out[(b["task"][:32], b["req_id"])] = str(b["label"]).lower()
            if str(b.get("confidence", "")).lower() == "low":
                out[("low_confidence", b["task"][:32], b["req_id"])] = True
    return out


STRICT_OUT = {("enterpriseops-teams-2725d17f", "R2_audio_call_source_james_target_alice"),
              ("automationbench-sales-partnershi", "R4_single_envelope")}


def in_task(r, mode, blind_prompt):
    if mode == "explicit_only":
        return r["prompt"] == "explicit"
    if mode == "blind":
        return blind_prompt.get((r["task"], r["id"])) in ("explicit", "derivable")
    if mode == "blind_strict":
        k = (r["task"], r["id"])
        return (blind_prompt.get(k) in ("explicit", "derivable") and not blind_prompt.get(("low_confidence",) + k)
                and k not in STRICT_OUT)
    return r["prompt"] in ("explicit", "derivable")


def upstream_of(q, gen, misled):
    if misled.get(gen):
        return "writer_misled"
    return TRACE_MAP.get((q or {}).get("stage", {}).get(gen), "untraced")


def opened_relevant(t, r, gen, access):
    if t["arm"] in INPROMPT:
        return "pasted"
    acc = access.get(t["trial"], {})
    f = r["memory_file"].get(gen)
    if acc.get("opened") and f and any(x.endswith(f) for x in acc.get("targets", [])):
        return "opened"
    return None


def stage_of(t, r, q, access, misled, mode, blind_prompt):
    if in_task(r, mode, blind_prompt):
        return "in_task_missed"
    arm = t["arm"]
    if arm in ("control", "placebo"):
        return "no_memory_arm"
    if arm == "evidence":
        return "raw_records_arm"
    if arm == "blend":
        return "blend_arm"
    gen = MEMORY_OF[arm]
    up = upstream_of(q, gen, misled)
    if up != "in_notes":
        return up
    if opened_relevant(t, r, gen, access):
        return "used_still_failed"
    return "not_shown_by_design" if arm == "noneshown" else "not_opened"


def run(D, reqs, failed, trace, access, misled, mode, blind_prompt):
    inst = collections.defaultdict(list)
    counts = collections.Counter()
    by_arm = collections.defaultdict(collections.Counter)
    distinct = {g: collections.defaultdict(set) for g in ("run1", "run3", "run4")}
    for t in failed:
        for r in reqs:
            if r["task"] != t["task"] or D.out[(t["trial"], r["key"])] != 0:
                continue
            q = trace.get((r["task"], r["id"]))
            s = stage_of(t, r, q, access, misled.get((r["task"], r["id"]), {}), mode, blind_prompt)
            inst[t["trial"]].append(s)
            counts[s] += 1
            by_arm[t["arm"]][s] += 1
            if t["arm"] in MEMORY_OF and t["arm"] != "blend":
                distinct[MEMORY_OF[t["arm"]]][s].add(r["key"])
    any_stage, only_stage = collections.Counter(), collections.Counter()
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
    notes_failed = [t for t in failed if t["arm"] in NOTES_ARMS]
    could_flip = [t for t in notes_failed if "in_task_missed" not in inst[t["trial"]]]
    present = [s for s in WRITER_FIRST if counts[s]] + sorted(s for s in counts if s not in WRITER_FIRST)
    return {
        "prompt_mode": mode,
        "trial_requirements_by_stage": {s: counts[s] for s in present},
        "trials_with_any_failure_at_stage": {s: any_stage[s] for s in present},
        "trials_whose_failures_are_all_one_stage": {s: only_stage[s] for s in present if only_stage[s]},
        "trials_with_mixed_stages": sum(1 for t in failed if len(set(inst[t["trial"]])) > 1),
        "waterfall_writer_first": waterfall(WRITER_FIRST),
        "waterfall_in_task_first": waterfall(IN_TASK_FIRST),
        "notes_arm_failed_trials": len(notes_failed),
        "notes_arm_failed_trials_with_no_in_task_failure": len(could_flip),
        "notes_arm_failed_trials_with_no_in_task_failure_by_task": dict(collections.Counter(t["task"] for t in could_flip)),
        "distinct_requirements_by_generation_and_stage": {g: {s: len(v) for s, v in d.items()} for g, d in distinct.items()},
        "trial_requirements_by_arm_and_stage": {a: {s: by_arm[a][s] for s in present if by_arm[a][s]} for a in ARMS},
    }


def main(private, blind, out_path, blind_prompt_glob=None):
    checks, access, reqs, _ = load(private, blind)
    D = Data(checks, reqs)
    trace = load_trace(private)
    misled = load_misleading(blind)
    blind_prompt = load_blind_prompt(blind_prompt_glob)
    failed = [t for t in D.trials if t["reward"] < 1]

    opened_partial = collections.Counter()
    in_task_notes_cover = collections.Counter()
    for t in failed:
        if t["arm"] not in NOTES_ARMS:
            continue
        gen = MEMORY_OF[t["arm"]]
        for r in reqs:
            if r["task"] != t["task"] or D.out[(t["trial"], r["key"])] != 0:
                continue
            lv = r["memory"].get(gen)
            mis = misled.get((r["task"], r["id"]), {}).get(gen)
            how = opened_relevant(t, r, gen, access)
            primary = stage_of(t, r, trace.get((r["task"], r["id"])), access, misled.get((r["task"], r["id"]), {}), "blind" if blind_prompt else "auditor", blind_prompt)
            if how and (lv in ("partial", "yes") or mis):
                opened_partial[("misleading" if mis else lv, how, primary)] += 1
            if primary == "in_task_missed" and lv in ("yes", "partial"):
                in_task_notes_cover[lv] += 1

    corpus_all = collections.Counter()
    kind_all = collections.Counter()
    upstream_all = {g: collections.Counter() for g in ("run1", "run3", "run4")}
    for t in failed:
        for r in reqs:
            if r["task"] != t["task"] or D.out[(t["trial"], r["key"])] != 0:
                continue
            q = trace.get((r["task"], r["id"])) or {}
            st = (q.get("corpus") or {}).get("status", "untraced")
            kinds = (q.get("corpus") or {}).get("kinds") or []
            corpus_all[st] += 1
            same = any(k.startswith("same_task") for k in kinds)
            strong_same = any(k in ("same_task_passing_run", "same_task_verifier_feedback") for k in kinds)
            kind_all[(st, "same_task_pass_or_feedback" if strong_same else "same_task_failing_hint_only" if same else "other_tasks_only" if st != "absent" else "none")] += 1
            for g in upstream_all:
                upstream_all[g][upstream_of(q, g, misled.get((r["task"], r["id"]), {}))] += 1

    req_level = []
    for r in reqs:
        q = trace.get((r["task"], r["id"])) or {}
        nfail = sum(1 for t in failed if t["task"] == r["task"] and D.out[(t["trial"], r["key"])] == 0)
        req_level.append({"key": r["key"], "prompt_auditor": r["prompt"], "prompt_blind": blind_prompt.get((r["task"], r["id"])),
                          "failed_trials": nfail, "corpus": (q.get("corpus") or {}).get("status"),
                          "corpus_kinds": (q.get("corpus") or {}).get("kinds"), "stage": q.get("stage"),
                          "misleading": misled.get((r["task"], r["id"])), "unstated_spec": (q.get("unstated_spec") or {}).get("value")})

    modes = ["auditor", "explicit_only"] + (["blind", "blind_strict"] if blind_prompt else [])
    out = {
        "failed_trials": len(failed),
        "failed_trial_requirements": sum(1 for t in failed for r in reqs if r["task"] == t["task"] and D.out[(t["trial"], r["key"])] == 0),
        "by_prompt_mode": {m: run(D, reqs, failed, trace, access, misled, m, blind_prompt) for m in modes},
        "opened_or_pasted_partial_or_misleading_and_failed": {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in sorted(opened_partial.items())},
        "opened_or_pasted_partial_or_misleading_and_failed_total": sum(opened_partial.values()),
        "in_task_missed_where_notes_also_cover": dict(in_task_notes_cover),
        "all_failed_trial_requirements_by_corpus_status": dict(corpus_all),
        "all_failed_trial_requirements_by_corpus_status_and_kind": {f"{a}|{b}": v for (a, b), v in sorted(kind_all.items())},
        "all_failed_trial_requirements_by_upstream_stage_per_generation": {g: dict(c) for g, c in upstream_all.items()},
        "prompt_label_agreement_auditor_vs_blind": dict(collections.Counter((r["prompt"], blind_prompt.get((r["task"], r["id"]))) for r in reqs)) if blind_prompt else None,
        "notes_also_cover_mode": "blind" if blind_prompt else "auditor",
        "requirements": req_level,
        "untraced_requirements": sorted({f"{r['task']}:{r['id']}" for r in reqs if (r["task"], r["id"]) not in trace}),
    }
    if out["prompt_label_agreement_auditor_vs_blind"]:
        out["prompt_label_agreement_auditor_vs_blind"] = {f"{a}|{b}": v for (a, b), v in out["prompt_label_agreement_auditor_vs_blind"].items()}
    json.dump(out, open(out_path, "w"), indent=1)
    short = {k: v for k, v in out.items() if k not in ("requirements",)}
    for m in short["by_prompt_mode"].values():
        m.pop("trial_requirements_by_arm_and_stage", None)
    print(json.dumps(short, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
