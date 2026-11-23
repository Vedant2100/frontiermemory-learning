"""Where the 65 passing trials, and every met requirement, got their information.

The mirror of stages.py and aggregation.py for successes: per arm with all-trial
denominators, per distinct requirement, and pooled only as labelled reference.
Counts only; no corpus or task text.

Usage: python3 successes.py PRIVATE BLIND_NOTES_LABELS BLIND_PROMPT_GLOB OUT_JSON
"""
import sys, json, glob, collections, random
from analysis import load, Data, MEMORY_OF, ARMS
import stages as S

DISC = {"explicit": "stated", "direct": "prompt_points_to_source", "one-step": "one_obvious_place", "search": "search_or_choice"}
NO_NOTES = {"control": "no_memory", "placebo": "no_memory", "evidence": "raw_records", "blend": "blend_notes_unlabelled"}


def load_disc(prompt_glob):
    out = {}
    for f in sorted(glob.glob(prompt_glob)):
        for b in json.load(open(f)):
            lab = str(b["label"]).lower()
            out[(b["task"][:32], b["req_id"])] = DISC.get("explicit" if lab == "explicit" else str(b.get("discoverability")), "not_in_task")
    return out


def main(private, blind, prompt_glob, out_path):
    checks, access, reqs, _ = load(private, blind)
    D = Data(checks, reqs)
    misled = S.load_misleading(blind)
    bp = S.load_blind_prompt(prompt_glob)
    disc = load_disc(prompt_glob)

    def intask(r):
        return S.in_task(r, "blind", bp)

    def scored_in(t):
        return [r for r in reqs if r["task"] == t["task"] and D.out[(t["trial"], r["key"])] is not None]

    def source(t, r):
        a = t["arm"]
        if a in NO_NOTES:
            if a == "evidence":
                return "raw_records_opened" if access.get(t["trial"], {}).get("opened") else "raw_records_not_opened"
            return NO_NOTES[a]
        gen = MEMORY_OF[a]
        lv = r["memory"].get(gen)
        read = S.opened_relevant(t, r, gen, access)
        if misled.get((r["task"], r["id"]), {}).get(gen):
            return "notes_misleading_read" if read else "notes_misleading_not_read"
        if lv == "yes":
            return "notes_cover_read" if read else "notes_cover_not_read"
        if lv == "partial":
            return "notes_partly_cover_read" if read else "notes_partly_cover_not_read"
        return "notes_silent"

    passes = [t for t in D.trials if t["reward"] >= 1]
    out = {"passing_trials": len(passes)}

    task_needs_outside = {}
    for task, ts in D.by_task.items():
        rs = {r["key"]: r for t in ts for r in scored_in(t)}
        task_needs_outside[task] = sorted(k for k, r in rs.items() if not intask(r))
    out["tasks_passed"] = dict(collections.Counter(t["task"] for t in passes).most_common())
    out["not_in_task_requirements_per_passed_task"] = {k: len(task_needs_outside[k]) for k in out["tasks_passed"]}

    per_trial = []
    for t in passes:
        outside = [r for r in scored_in(t) if not intask(r)]
        srcs = [source(t, r) for r in outside]
        if not outside:
            cls = "task_gave_everything"
        elif all(s in ("notes_cover_read", "notes_partly_cover_read") for s in srcs):
            cls = "outside_info_all_from_notes_read"
        elif any(s in ("notes_cover_read", "notes_partly_cover_read") for s in srcs):
            cls = "outside_info_partly_from_notes_read"
        elif any(s == "raw_records_opened" for s in srcs):
            cls = "raw_records_opened"
        else:
            cls = "outside_info_met_without_reading_a_covering_source"
        searched = any(disc.get((r["task"], r["id"])) == "search_or_choice" for r in scored_in(t))
        per_trial.append({"arm": t["arm"], "task": t["task"], "class": cls, "sources": srcs, "needed_search_or_choice": searched})

    by_arm = {}
    for a in ARMS:
        rows = [p for p in per_trial if p["arm"] == a]
        by_arm[a] = {"passes": len(rows), "of": sum(1 for t in D.trials if t["arm"] == a),
                     "by_task": dict(collections.Counter(p["task"] for p in rows)),
                     "by_class": dict(collections.Counter(p["class"] for p in rows)),
                     "needed_search_or_choice": sum(p["needed_search_or_choice"] for p in rows)}
    out["passes_by_arm"] = by_arm
    out["passes_by_task_and_class"] = {k: dict(collections.Counter(p["class"] for p in per_trial if p["task"] == k)) for k in out["tasks_passed"]}
    out["outside_requirement_sources_in_passes"] = dict(collections.Counter(s for p in per_trial for s in p["sources"]))

    met_in, met_out = {}, {}
    for a in ARMS:
        ci, co = collections.Counter(), collections.Counter()
        for t in D.trials:
            if t["arm"] != a:
                continue
            for r in scored_in(t):
                v = D.out[(t["trial"], r["key"])]
                if intask(r):
                    d = disc.get((r["task"], r["id"]), "unlabelled")
                    ci[d + "|cells"] += 1
                    ci[d + "|met"] += v
                else:
                    s = source(t, r)
                    co[s + "|cells"] += 1
                    co[s + "|met"] += v
        met_in[a] = dict(ci)
        met_out[a] = dict(co)
    out["in_task_met_by_discoverability_and_arm"] = met_in
    out["not_in_task_met_by_source_and_arm"] = met_out

    pooled_in = collections.Counter()
    for a in ARMS:
        for k, v in met_in[a].items():
            pooled_in[k] += v
    out["in_task_met_by_discoverability_pooled_reference"] = dict(pooled_in)

    dist = {}
    for r in reqs:
        if intask(r):
            continue
        cells = {a: D.cell(r["key"], a) for a in ARMS}
        if not any(cells.values()):
            continue
        dist[r["key"]] = {a: f"{sum(v)}/{len(v)}" for a, v in cells.items() if v}
    out["not_in_task_requirements_met_per_arm"] = dist
    summ = collections.Counter()
    for k, d in dist.items():
        base = [d[a] for a in ("control", "placebo") if a in d]
        base_met = sum(int(x.split("/")[0]) for x in base)
        mem_met = sum(int(x.split("/")[0]) for a, x in d.items() if a not in ("control", "placebo"))
        if not base:
            summ["no_control_measure"] += 1
        elif base_met:
            summ["met_without_memory_at_least_once"] += 1
        elif mem_met:
            summ["met_only_with_memory_or_records"] += 1
        else:
            summ["never_met"] += 1
    out["not_in_task_requirements_summary"] = dict(summ)

    in_dist = collections.Counter()
    for r in reqs:
        if not intask(r):
            continue
        cells = [v for a in ARMS for v in D.cell(r["key"], a)]
        if not cells:
            continue
        d = disc.get((r["task"], r["id"]), "unlabelled")
        in_dist[d + "|requirements"] += 1
        in_dist[d + "|always_met"] += all(cells)
        in_dist[d + "|never_met"] += not any(cells)
    out["in_task_distinct_requirements_by_discoverability"] = dict(in_dist)

    by_cell = collections.defaultdict(lambda: collections.defaultdict(list))
    for t in D.trials:
        by_cell[t["arm"]][t["task"]].append(t)

    def met_search(t):
        return sum(D.out[(t["trial"], r["key"])] for r in scored_in(t)
                   if intask(r) and disc.get((r["task"], r["id"])) == "search_or_choice")

    def perm(a, b="control", n=2000, seed=4):
        rng = random.Random(seed)
        tasks = [k for k in by_cell[b] if by_cell[a].get(k)]
        obs = sum(met_search(t) for k in tasks for t in by_cell[a][k]) - sum(met_search(t) for k in tasks for t in by_cell[b][k])
        ge = 0
        for _ in range(n):
            s = 0
            for k in tasks:
                pool = by_cell[a][k] + by_cell[b][k]
                rng.shuffle(pool)
                m = len(by_cell[a][k])
                s += sum(met_search(t) for t in pool[:m]) - sum(met_search(t) for t in pool[m:])
            ge += abs(s) >= abs(obs)
        return {"diff": obs, "perm_p_two_sided": round(ge / n, 3)}

    out["search_or_choice_met_arm_minus_control"] = {a: perm(a) for a in ARMS if a != "control"}

    json.dump(out, open(out_path, "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ("not_in_task_requirements_met_per_arm",)}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
