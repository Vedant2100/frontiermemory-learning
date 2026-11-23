"""Aggregation checks for the failure analysis: the stage counts per arm, per
generation and per distinct requirement, with all-trial denominators.

Each figure here replaces or qualifies a pooled count in REPORT.md (section 8
lists which). Counts only; no corpus text.

Usage: python3 aggregation.py PRIVATE BLIND_NOTES_LABELS BLIND_PROMPT_GLOB REQ_ANALYSIS_JSON OUT_JSON
"""
import sys, json, collections, random
from analysis import load, Data, MEMORY_OF, ARMS, trial_perm, mean
import stages as S

GENS = ("run1", "run3", "run4")


def main(private, blind, prompt_glob, req_json, out_path):
    checks, access, reqs, _ = load(private, blind)
    D = Data(checks, reqs)
    trace = S.load_trace(private)
    misled = S.load_misleading(blind)
    bp = S.load_blind_prompt(prompt_glob)
    rq = {r["key"]: r for r in reqs}
    failed = [t for t in D.trials if t["reward"] < 1]

    def intask(r):
        return S.in_task(r, "blind", bp)

    def fails(t):
        return [r for r in reqs if r["task"] == t["task"] and D.out[(t["trial"], r["key"])] == 0]

    def up(r, gen):
        return S.upstream_of(trace.get((r["task"], r["id"])), gen, misled.get((r["task"], r["id"]), {}))

    def corpus(r):
        return (trace.get((r["task"], r["id"])) or {}).get("corpus") or {}

    out = {}
    out["failed_requirements_in_passing_trials"] = sum(len(fails(t)) for t in D.trials if t["reward"] >= 1)

    cnt = collections.Counter(r["key"] for t in failed for r in fails(t))
    dist = sorted(cnt)
    scored = [r for r in reqs if any(D.out[(t["trial"], r["key"])] is not None for t in D.by_task[r["task"]])]
    out["units"] = {
        "failed_trial_requirements": sum(cnt.values()),
        "distinct_failed_requirements": len(dist),
        "scored_requirements": len(scored),
        "top8_requirements_share": sum(v for _, v in cnt.most_common(8)),
        "by_task": dict(collections.Counter(rq[k]["task"] for t in failed for r in fails(t) for k in [r["key"]]).most_common()),
        "distinct_failed_in_task": sum(1 for k in dist if intask(rq[k])),
        "distinct_failed_not_in_task": sum(1 for k in dist if not intask(rq[k])),
    }

    kinds = collections.Counter()
    for k in dist:
        c = corpus(rq[k])
        ks = c.get("kinds") or []
        strong = any(x in ("same_task_passing_run", "same_task_verifier_feedback") for x in ks)
        same = any(x.startswith("same_task") for x in ks)
        kinds[f"{c.get('status')}|" + ("same_task_pass_or_feedback" if strong else "same_task_failing_hint_only" if same else "other_tasks_only" if c.get("status") != "absent" else "none")] += 1
    out["corpus_distinct_failed_requirements"] = {
        "status": dict(collections.Counter(corpus(rq[k]).get("status") for k in dist)),
        "status_and_kind": dict(sorted(kinds.items())),
    }

    rng = random.Random(1)
    in_task_arm = {}
    for a in ARMS:
        ts = [t for t in D.trials if t["arm"] == a]
        cells = [(t, r) for t in ts for r in reqs if r["task"] == t["task"] and intask(r) and D.out[(t["trial"], r["key"])] is not None]
        miss = sum(1 for t, r in cells if D.out[(t["trial"], r["key"])] == 0)
        by = collections.defaultdict(list)
        for t in ts:
            by[t["task"]].append(t)
        def count(sample):
            return sum(1 for t in sample for r in fails(t) if intask(r))
        boots = sorted(sum(count([rng.choice(v) for _ in v]) for v in by.values()) for _ in range(2000))
        nit = [(t, r) for t in ts for r in reqs if r["task"] == t["task"] and not intask(r) and D.out[(t["trial"], r["key"])] is not None]
        nmiss = sum(1 for t, r in nit if D.out[(t["trial"], r["key"])] == 0)
        in_task_arm[a] = {"in_task_cells": len(cells), "in_task_missed": miss, "in_task_miss_rate": round(miss / len(cells), 3),
                          "in_task_missed_95": [boots[50], boots[1949]],
                          "not_in_task_cells": len(nit), "not_in_task_missed": nmiss, "not_in_task_miss_rate": round(nmiss / len(nit), 3)}
    out["miss_rates_by_arm_all_trials"] = in_task_arm

    nw = {}
    for a in ARMS:
        cells = [(t, r) for t in D.trials if t["arm"] == a and "word2vec" not in t["task"]
                 for r in reqs if r["task"] == t["task"] and not intask(r) and D.out[(t["trial"], r["key"])] is not None]
        miss = [(t, r) for t, r in cells if D.out[(t["trial"], r["key"])] == 0]
        nw[a] = {"cells": len(cells), "missed": len(miss), "rate": round(len(miss) / len(cells), 3),
                 "missed_by_task": dict(collections.Counter(t["task"] for t, _ in miss))}
    out["not_in_task_miss_by_arm_excluding_word2vec"] = nw

    def misses(t, want_in_task):
        if want_in_task is False and "word2vec" in t["task"]:
            return 0
        return sum(1 for r in reqs if r["task"] == t["task"] and intask(r) == want_in_task and D.out[(t["trial"], r["key"])] == 0)

    by_cell = collections.defaultdict(lambda: collections.defaultdict(list))
    for t in D.trials:
        by_cell[t["arm"]][t["task"]].append(t)

    def contrast(a, b, want_in_task, seed=2, n=2000):
        rng2 = random.Random(seed)
        tasks = [k for k in by_cell[b] if by_cell[a].get(k)]
        def total(arm, pick):
            return sum(misses(t, want_in_task) for k in tasks for t in pick(by_cell[arm][k]))
        obs = total(a, lambda v: v) - total(b, lambda v: v)
        bs = []
        for _ in range(n):
            bs.append(total(a, lambda v: [rng2.choice(v) for _ in v]) - total(b, lambda v: [rng2.choice(v) for _ in v]))
        bs.sort()
        ge = 0
        for _ in range(n):
            s = 0
            for k in tasks:
                pool = by_cell[a][k] + by_cell[b][k]
                rng2.shuffle(pool)
                m = len(by_cell[a][k])
                s += sum(misses(t, want_in_task) for t in pool[:m]) - sum(misses(t, want_in_task) for t in pool[m:])
            ge += abs(s) >= abs(obs)
        return {"diff": obs, "boot_95": [bs[int(0.025 * n)], bs[int(0.975 * n) - 1]], "perm_p_two_sided": round(ge / n, 3)}

    out["arm_minus_control_misses"] = {
        "method": "missed requirement-trials, arm minus control; bootstrap resamples trials within task, permutation shuffles arm labels within task",
        "in_task": {a: contrast(a, "control", True) for a in ARMS if a != "control"},
        "not_in_task_excluding_word2vec": {a: contrast(a, "control", False) for a in ARMS if a != "control"},
        "in_task_raw_records_minus_blend": contrast("evidence", "blend", True),
    }

    expo = {}
    for a in S.NOTES_ARMS:
        gen = MEMORY_OF[a]
        e = f = 0
        for t in D.trials:
            if t["arm"] != a:
                continue
            for r in reqs:
                if r["task"] != t["task"]:
                    continue
                v = D.out[(t["trial"], r["key"])]
                if v is None:
                    continue
                if not (r["memory"].get(gen) == "partial" or misled.get((r["task"], r["id"]), {}).get(gen)):
                    continue
                if not S.opened_relevant(t, r, gen, access):
                    continue
                e += 1
                f += (v == 0)
        expo[a] = {"exposures": e, "failed": f}
    out["partial_or_misleading_note_opened_or_pasted_by_arm"] = expo

    tab = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for t in D.trials:
        if t["arm"] not in S.NOTES_ARMS:
            continue
        gen = MEMORY_OF[t["arm"]]
        for r in reqs:
            if r["task"] != t["task"] or r["memory"].get(gen) != "partial":
                continue
            v = D.out[(t["trial"], r["key"])]
            if v is None:
                continue
            how = S.opened_relevant(t, r, gen, access) or ("opened_other" if access.get(t["trial"], {}).get("opened") else "none")
            tab[t["task"]][how][0] += v
            tab[t["task"]][how][1] += 1
    opened_tasks = [k for k, d in tab.items() if d["opened"][1]]
    out["partial_notes_met_by_task"] = {k: {h: f"{v[0]}/{v[1]}" for h, v in d.items()} for k, d in sorted(tab.items())}
    out["partial_notes_not_opened_in_tasks_with_an_open"] = [sum(tab[k]["none"][0] for k in opened_tasks), sum(tab[k]["none"][1] for k in opened_tasks)]

    cp = {}
    for gen in GENS:
        cp[gen] = dict(collections.Counter(up(r, gen) for t in failed if t["arm"] in ("control", "placebo") for r in fails(t) if not intask(r)))
    cp["in_any_generation"] = sum(1 for t in failed if t["arm"] in ("control", "placebo") for r in fails(t)
                                  if not intask(r) and any(up(r, g) == "in_notes" for g in GENS))
    out["control_placebo_not_in_task_by_generation"] = cp

    out["generation_stage_distinct"] = {g: {
        "scored_requirements": dict(collections.Counter(up(r, g) for r in scored)),
        "scored_not_in_task": dict(collections.Counter(up(r, g) for r in scored if not intask(r))),
    } for g in GENS}

    own = {}
    for g in GENS:
        c = collections.Counter()
        for t in failed:
            if t["arm"] in S.NOTES_ARMS and MEMORY_OF[t["arm"]] == g:
                for r in fails(t):
                    c["in_task" if intask(r) else up(r, g)] += 1
        own[g] = dict(c)
    out["notes_arms_failed_trial_requirements_by_own_generation"] = own

    ct = {}
    for lvl in ("yes", "partial", "no"):
        per_task, per_arm = collections.defaultdict(list), collections.defaultdict(list)
        for r in reqs:
            cc = D.cell(r["key"], "control")
            if not cc:
                continue
            for arm, mem in MEMORY_OF.items():
                if mem == "blend" or r["memory"].get(mem) != lvl:
                    continue
                aa = D.cell(r["key"], arm)
                if aa:
                    d = sum(aa) / len(aa) - sum(cc) / len(cc)
                    per_task[r["task"]].append(d)
                    per_arm[arm].append(d)
        rg = []
        for r in reqs:
            cc = D.cell(r["key"], "control")
            if not cc:
                continue
            for g in GENS:
                if r["memory"].get(g) != lvl:
                    continue
                xs = [x for a, m in MEMORY_OF.items() if m == g for x in D.cell(r["key"], a)]
                if xs:
                    rg.append(sum(xs) / len(xs) - sum(cc) / len(cc))
        ct[lvl] = {"by_task": {k: [len(v), round(mean(v), 3)] for k, v in per_task.items()},
                   "by_arm": {k: [len(v), round(mean(v), 3)] for k, v in per_arm.items()},
                   "requirement_x_generation_units": len(rg), "requirement_x_generation_mean": round(mean(rg), 3) if rg else None}
    for arms, name in (({"control", "run1", "run3", "run4"}, "indexed_arms_run1_run3_run4"),):
        sel = {a: m for a, m in MEMORY_OF.items() if a in arms}
        def stat(L, sel=sel):
            ds = []
            for r in reqs:
                c = D.cell(r["key"], "control", L)
                if not c:
                    continue
                for arm, mem in sel.items():
                    if r["memory"].get(mem) != "yes":
                        continue
                    a = D.cell(r["key"], arm, L)
                    if a:
                        ds.append(sum(a) / len(a) - sum(c) / len(c))
            return mean(ds)
        obs, p = trial_perm(D, stat, 2000, 11, arms)
        ct["yes_" + name] = {"diff": round(obs, 3), "p": round(p, 4)}
    out["content_test_breakdown"] = ct

    lad = json.load(open(req_json))["exposure_ladder"]["run1_yes"]["per_task"]
    tb = {}
    for a in ["control", "placebo", "noneshown", "run1", "readfirst", "allshown"]:
        rates = [int(d[a].split("/")[0]) / int(d[a].split("/")[1]) for d in lad.values() if int(d[a].split("/")[1])]
        tb[a] = round(sum(rates) / len(rates), 3)
    out["ladder_task_balanced"] = tb

    J, trs, ks = collections.Counter(), set(), set()
    for t in D.trials:
        if t["arm"] not in S.NOTES_ARMS:
            continue
        gen = MEMORY_OF[t["arm"]]
        for r in reqs:
            if r["task"] != t["task"] or r["memory"].get(gen) != "yes":
                continue
            v = D.out[(t["trial"], r["key"])]
            if v is None or not S.opened_relevant(t, r, gen, access):
                continue
            J[f"{t['arm']}|met" if v == 1 else f"{t['arm']}|failed"] += 1
            trs.add(t["trial"])
            ks.add(r["key"])
    out["fully_covered_opened_or_pasted"] = {"cells": sum(J.values()), "trials": len(trs), "requirements": len(ks), "by_arm": dict(J)}

    ceil = {}
    for a in ARMS:
        ts = [t for t in D.trials if t["arm"] == a]
        passes = sum(1 for t in ts if t["reward"] >= 1)
        flip = sum(1 for t in ts if t["reward"] < 1 and not any(intask(r) for r in fails(t)))
        ceil[a] = {"trials": len(ts), "passes": passes, "failed_no_in_task_miss": flip, "ceiling_if_all_not_in_task_info_supplied": passes + flip}
    out["pass_ceiling_by_arm"] = ceil

    out["auditor_vs_blind_in_task_failed_trial_requirements"] = {
        f"auditor_{a}|blind_{b}": v for (a, b), v in collections.Counter(
            (r["prompt"] in ("explicit", "derivable"), intask(r)) for t in failed for r in fails(t)).items()}

    json.dump(out, open(out_path, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:6])
