"""Requirement-level failure analysis for the FrontierMemory study.

Inputs (private, read-only): checks.jsonl, access.jsonl and the per-task audit
JSON files; optionally a file of outcome-blind memory labels. Output: one JSON
of derived tables, with no raw task or memory text.
Usage: python3 analysis.py PRIVATE_DIR OUT_JSON [BLIND_LABELS_JSON]

Conventions:
- A requirement's outcome in a trial is pass (1), fail (0) or unmeasured (None).
  It is unmeasured when none of its checks ran (verifier could not load the
  solution, or the hidden test file failed to compile); those checks were
  filled in by checks.py and are not evidence about the requirement.
- Content level of an arm's notes for a requirement: yes / partial / no. With
  blind labels, only run1, run3 and run4 notes are labelled; blend is then left
  out of every content-based comparison, because its labels are not blind.
"""
import json, glob, os, sys, random, collections, statistics

ARMS = ["control", "run1", "run3", "run4", "placebo", "readfirst",
        "allshown", "noneshown", "evidence", "blend"]
MEMORY_OF = {"run1": "run1", "readfirst": "run1", "allshown": "run1",
             "noneshown": "run1", "run3": "run3", "run4": "run4", "blend": "blend"}
INPROMPT = {"allshown", "blend"}
LADDER = ["control", "placebo", "noneshown", "run1", "readfirst", "allshown"]


def level(x):
    v = x.get("value", x.get("label", x.get("contains"))) if isinstance(x, dict) else x
    v = str(v or "no").lower()
    return "yes" if v.startswith("yes") else "partial" if v.startswith("partial") else "no"


def prompt_level(x):
    v = str(x.get("value", x) if isinstance(x, dict) else x).lower()
    for k in ("explicit", "derivable", "absent"):
        if v.startswith(k):
            return k
    return "unknown"


def load(private, blind_path):
    checks = [json.loads(l) for l in open(os.path.join(private, "checks.jsonl"))]
    access = {r["trial"]: r for r in (json.loads(l) for l in open(os.path.join(private, "access.jsonl")))}
    blind = None
    if blind_path:
        blind = {(b["task"], b["req_id"]): b for b in json.load(open(blind_path))}
    reqs = []
    for f in sorted(glob.glob(os.path.join(private, "causal", "audit", "*.json"))):
        d = json.load(open(f))
        task = d["task"][:32]
        for q in d["requirements"]:
            mem = q.get("memory_content", {})
            blind_file = {}
            audit_mem = {m: level(mem.get(m)) for m in ("run1", "run3", "run4", "blend")}
            memory = dict(audit_mem)
            if blind is not None:
                b = blind[(d["task"], q["id"])]
                for m in ("run1", "run3", "run4"):
                    memory[m] = level(b[m])
                memory["blend"] = None
                blind_file = {m: os.path.basename(str(b[m].get("path") or "")) for m in ("run1", "run3", "run4") if isinstance(b[m], dict)}
            reqs.append({
                "task": task, "id": q["id"], "key": f"{task}:{q['id']}", "checks": q["checks"],
                "prompt": prompt_level(q.get("prompt_states")), "memory": memory, "audit_memory": audit_mem,
                "memory_file": blind_file or {m: os.path.basename(str((mem.get(m) or {}).get("path", "")))
                                              for m in ("run1", "run3", "run4") if isinstance(mem.get(m), dict)},
            })
    return checks, access, reqs, blind is not None


def outcome(trial, r):
    cs = [c for c in r["checks"] if c in trial["checks"]]
    if not cs:
        return None
    filled = set(trial.get("filled") or [])
    if trial["kind"] != "assertions":
        cs = [c for c in cs if c not in filled]
        if not cs:
            return None
    return int(all(trial["checks"][c] for c in cs))


def mean(xs):
    return statistics.mean(xs) if xs else None


def rnd(x, k=3):
    return None if x is None else round(x, k)


class Data:
    def __init__(self, checks, reqs):
        self.trials = [t for t in checks if t["arm"] != "oracle"]
        self.reqs = reqs
        self.by_task = collections.defaultdict(list)
        for t in self.trials:
            self.by_task[t["task"]].append(t)
        self.out = {}
        for t in self.trials:
            for r in reqs:
                if r["task"] == t["task"]:
                    self.out[(t["trial"], r["key"])] = outcome(t, r)
        self.groups = self.group({t["trial"]: t["arm"] for t in self.trials})

    def group(self, labels):
        g = collections.defaultdict(list)
        for t in self.trials:
            g[(t["task"], labels[t["trial"]])].append(t["trial"])
        return g

    def cell(self, key, arm, groups=None):
        task = key.split(":")[0]
        g = groups if groups is not None else self.groups
        return [v for v in (self.out[(tr, key)] for tr in g.get((task, arm), ())) if v is not None]


def content_units(D, lvl, labels=None, contested_only=False, exclude_tasks=()):
    diffs, tasks = [], set()
    for r in D.reqs:
        if r["task"] in exclude_tasks:
            continue
        c = D.cell(r["key"], "control", labels)
        if not c:
            continue
        for arm, mem in MEMORY_OF.items():
            if r["memory"].get(mem) != lvl:
                continue
            a = D.cell(r["key"], arm, labels)
            if not a:
                continue
            if contested_only and sum(a + c) in (0, len(a + c)):
                continue
            diffs.append(sum(a) / len(a) - sum(c) / len(c))
            tasks.add(r["task"])
    return diffs, tasks


def trial_perm(D, stat, n, seed, arms):
    """Permute arm labels of whole trials within each task, among `arms`.
    Keeps every requirement of a trial together and keeps shared control trials shared."""
    rng = random.Random(seed)
    obs = stat(None)
    hits = 0
    for _ in range(n):
        labels = {}
        for task, ts in D.by_task.items():
            pool = [t for t in ts if t["arm"] in arms]
            arm_list = [t["arm"] for t in pool]
            rng.shuffle(arm_list)
            for t, a in zip(pool, arm_list):
                labels[t["trial"]] = a
            for t in ts:
                labels.setdefault(t["trial"], t["arm"])
        v = stat(D.group(labels))
        if v is not None and v >= obs - 1e-12:
            hits += 1
    return obs, (hits + 1) / (n + 1)


def task_boot(D, lvl, n=4000, seed=3):
    rng = random.Random(seed)
    per_task = collections.defaultdict(list)
    for r in D.reqs:
        c = D.cell(r["key"], "control")
        for arm, mem in MEMORY_OF.items():
            if not c or r["memory"].get(mem) != lvl:
                continue
            a = D.cell(r["key"], arm)
            if a:
                per_task[r["task"]].append(sum(a) / len(a) - sum(c) / len(c))
    tasks = list(per_task)
    if len(tasks) < 2:
        return None
    vals = sorted(mean([x for t in (rng.choice(tasks) for _ in tasks) for x in per_task[t]]) for _ in range(n))
    return [rnd(vals[int(0.025 * n)]), rnd(vals[int(0.975 * n)])]


def ladder_rates(D, keys, labels=None):
    row = {}
    for arm in LADDER:
        xs = [x for k in keys for x in D.cell(k, arm, labels)]
        row[arm] = (sum(xs) / len(xs), len(xs)) if xs else (None, 0)
    return row


def trend(D, keys, labels=None):
    """Mean over requirements of the correlation between ladder rank and outcome."""
    rs = []
    for k in keys:
        xs, ys = [], []
        for i, arm in enumerate(LADDER):
            for v in D.cell(k, arm, labels):
                xs.append(i)
                ys.append(v)
        if len(set(ys)) < 2:
            rs.append(0.0)
            continue
        mx, my = mean(xs), mean(ys)
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        sxx = sum((x - mx) ** 2 for x in xs)
        syy = sum((y - my) ** 2 for y in ys)
        rs.append(sxy / (sxx * syy) ** 0.5)
    return mean(rs)


def main(private, out_path, blind_path=None):
    checks, access, reqs, is_blind = load(private, blind_path)
    D = Data(checks, reqs)
    rq = {r["key"]: r for r in reqs}

    req_table = []
    for r in reqs:
        per_arm = {a: D.cell(r["key"], a) for a in ARMS}
        allx = [x for a in ARMS for x in per_arm[a]]
        status = ("never_scored" if not allx else "never_met" if sum(allx) == 0
                  else "always_met" if sum(allx) == len(allx) else "contested")
        r["status"] = status
        req_table.append({"key": r["key"], "task": r["task"], "id": r["id"], "n_checks": len(r["checks"]),
                          "prompt": r["prompt"], "memory": r["memory"], "status": status,
                          "met": sum(allx), "measured": len(allx),
                          "by_arm": {a: f"{sum(v)}/{len(v)}" for a, v in per_arm.items()}})

    content_arms = {"control"} | {a for a, m in MEMORY_OF.items() if not (is_blind and m == "blend")}
    content = {}
    for lvl in ("yes", "partial", "no"):
        diffs, tasks = content_units(D, lvl)
        if not diffs:
            continue
        obs, p = trial_perm(D, lambda L, lvl=lvl: mean(content_units(D, lvl, L)[0]), 2000, 11, content_arms)
        cdiffs, _ = content_units(D, lvl, contested_only=True)
        drops = {}
        for t in sorted(tasks):
            dd, _ = content_units(D, lvl, exclude_tasks=(t,))
            drops[t] = rnd(mean(dd))
        content[lvl] = {"units": len(diffs), "tasks": sorted(tasks), "mean_diff": rnd(obs), "p_one_sided_trial_perm": rnd(p, 4),
                        "ci95_task_boot": task_boot(D, lvl), "contested_only_mean_diff": rnd(mean(cdiffs)),
                        "contested_only_units": len(cdiffs), "leave_one_task_out": drops}

    pl = []
    for r in reqs:
        a, c = D.cell(r["key"], "placebo"), D.cell(r["key"], "control")
        if a and c:
            pl.append(sum(a) / len(a) - sum(c) / len(c))
    placebo = {"units": len(pl), "mean_diff": rnd(mean(pl))}

    regression = {}
    for band, low in (("control_met_at_most_1_of_3", True), ("control_met_at_least_2_of_3", False)):
        row = {}
        for lvl in ("yes", "partial", "no", "placebo"):
            ds = []
            for r in reqs:
                c = D.cell(r["key"], "control")
                if not c or ((sum(c) / len(c) <= 1 / 3 + 1e-9) != low):
                    continue
                arms = ["placebo"] if lvl == "placebo" else [a for a, m in MEMORY_OF.items() if r["memory"].get(m) == lvl]
                for a in arms:
                    x = D.cell(r["key"], a)
                    if x:
                        ds.append(sum(x) / len(x) - sum(c) / len(c))
            row[lvl] = {"units": len(ds), "mean_diff": rnd(mean(ds))}
        regression[band] = row

    ladder = {}
    for lvl in ("yes", "partial", "no"):
        keys = [r["key"] for r in reqs if r["memory"]["run1"] == lvl and r["status"] == "contested"]
        if not keys:
            continue
        rates = ladder_rates(D, keys)
        obs, p = trial_perm(D, lambda L, keys=keys: trend(D, keys, L), 2000, 13, set(LADDER))
        per_task = {}
        for t in sorted({rq[k]["task"] for k in keys}):
            tk = [k for k in keys if rq[k]["task"] == t]
            per_task[t] = {a: f"{sum(x for k in tk for x in D.cell(k, a))}/{sum(len(D.cell(k, a)) for k in tk)}" for a in LADDER}
        ladder[f"run1_{lvl}"] = {"requirements": len(keys), "tasks": sorted({rq[k]['task'] for k in keys}),
                                 "rates": {a: {"rate": rnd(v[0]), "n": v[1]} for a, v in rates.items()},
                                 "trend_r": rnd(obs), "trend_p_one_sided_trial_perm": rnd(p, 4), "per_task": per_task}

    def relevant_access(trial, arm, r):
        if arm in INPROMPT:
            return "in_prompt"
        acc = access.get(trial, {})
        if not acc.get("opened"):
            return "not_opened"
        f = r["memory_file"].get(MEMORY_OF[arm])
        if f and any(t.endswith(f) for t in acc.get("targets", [])):
            return "opened_relevant"
        return "opened_other"
    acc_tab = collections.defaultdict(lambda: [0, 0])
    for t in D.trials:
        if t["arm"] not in MEMORY_OF or (is_blind and t["arm"] == "blend"):
            continue
        for r in reqs:
            if r["task"] != t["task"] or r["memory"].get(MEMORY_OF[t["arm"]]) != "yes":
                continue
            v = D.out[(t["trial"], r["key"])]
            if v is None:
                continue
            k = relevant_access(t["trial"], t["arm"], r)
            acc_tab[k][0] += v
            acc_tab[k][1] += 1

    def info_class(t, r):
        if r["prompt"] in ("explicit", "derivable"):
            return "available"
        mem = MEMORY_OF.get(t["arm"])
        if t["arm"] == "evidence":
            return "absent_or_unread_records"
        lv = r["memory"].get(mem) if mem else None
        if lv == "yes":
            return "notes_only"
        if lv == "partial":
            return "notes_partial"
        return "absent"
    failed = [t for t in D.trials if t["reward"] < 1]
    inst = collections.defaultdict(list)
    for t in failed:
        for r in reqs:
            if r["task"] == t["task"] and D.out[(t["trial"], r["key"])] == 0:
                inst[t["trial"]].append((info_class(t, r), r["status"] == "never_met"))
    combos = collections.Counter("+".join(sorted({c for c, _ in inst[t["trial"]]})) or "none" for t in failed)
    steps = [("absent", {"absent", "absent_or_unread_records"}),
             ("partial", {"notes_partial"}),
             ("notes_only", {"notes_only"})]
    remaining = {t["trial"] for t in failed}
    cascade = []
    for name, cls in steps:
        hit = {tr for tr in remaining if any(c in cls for c, _ in inst[tr])}
        cascade.append({"step": name, "taken": len(hit), "match_any_order": sum(1 for t in failed if any(c in cls for c, _ in inst[t["trial"]]))})
        remaining -= hit
    cascade.append({"step": "available_only", "taken": len(remaining), "match_any_order": len(remaining)})
    never_met_trials = sum(1 for t in failed if any(w for _, w in inst[t["trial"]]))
    per_arm = collections.defaultdict(collections.Counter)
    for t in failed:
        cl = {c for c, _ in inst[t["trial"]]}
        k = ("absent" if cl & {"absent", "absent_or_unread_records"} else "partial" if "notes_partial" in cl
             else "notes_only" if "notes_only" in cl else "available_only")
        per_arm[t["arm"]][k] += 1
        per_arm[t["arm"]]["never_met"] += int(any(w for _, w in inst[t["trial"]]))

    strict = collections.defaultdict(collections.Counter)
    for t in D.trials:
        strict[t["task"]][t["arm"]] += int(t["reward"] >= 1)

    out = {
        "labels": "blind (run1/run3/run4); blend excluded from content comparisons" if is_blind else "auditor",
        "requirements": req_table,
        "content_test": content,
        "placebo_vs_control": placebo,
        "regression_to_mean_check": regression,
        "exposure_ladder": ladder,
        "access_when_notes_cover": {k: {"met": v[0], "n": v[1], "rate": rnd(v[0] / v[1])} for k, v in acc_tab.items()},
        "failed_trial_class_combinations": dict(combos.most_common()),
        "cascade": cascade,
        "failed_trials_with_a_never_met_requirement": never_met_trials,
        "per_arm_classes": {a: dict(per_arm[a]) for a in ARMS},
        "strict_passes": {t: dict(c) for t, c in strict.items()},
    }
    json.dump(out, open(out_path, "w"), indent=1)
    print(json.dumps({k: out[k] for k in ("content_test", "placebo_vs_control", "regression_to_mean_check",
                                          "access_when_notes_cover", "cascade", "failed_trials_with_a_never_met_requirement")}, indent=1))
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "per_task"} for k, v in ladder.items()}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
