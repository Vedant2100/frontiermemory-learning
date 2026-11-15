"""Opened-versus-not-opened comparison for run 1 and read-first (the two arms with a memory-access log).
Prints naive and within-task results. Reads results/official/*.jsonl only."""
import json, os, random, collections, statistics as st, datetime as dt
O = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "official")
L = lambda f: [json.loads(l) for l in open(os.path.join(O, f))]
ctl = collections.defaultdict(list)
for r in L("partial-credit-fm-tasks-control.jsonl"): ctl[r["trial"].rsplit("__", 1)[0]].append(r["partial"])
rows = []
for arm, name, s in (("run1", "run1", "run1"), ("readfirst", "readfirst", "arm-readfirst")):
    acc = {r["trial"]: r for r in L(f"memory-access-{name}.jsonl")}
    sm = {r["trial"]: r for r in L(f"summary-fm-tasks-{s}.jsonl")}
    pc = {r["trial"]: r for r in L(f"partial-credit-fm-tasks-{s}.jsonl")}
    for t, a in acc.items():
        task = t.rsplit("__", 1)[0]
        rows.append(dict(arm=arm, task=task, op=a["opened"], partial=pc[t]["partial"], passed=sm[t]["passed"], ctl=st.mean(ctl[task])))
for op in (True, False):
    R = [r for r in rows if r["op"] == op]
    print("opened" if op else "not opened", len(R), "trials,", sum(r["passed"] for r in R), "passes, mean partial", round(st.mean(r["partial"] for r in R), 3),
          ", mean partial minus control task mean", round(st.mean(r["partial"] - r["ctl"] for r in R), 3))
def within(rs):
    by = collections.defaultdict(lambda: {True: [], False: []})
    for r in rs: by[(r["arm"], r["task"])][r["op"]].append(r["partial"])
    d = [st.mean(v[True]) - st.mean(v[False]) for v in by.values() if v[True] and v[False]]
    return st.mean(d), len(d)
obs, n = within(rows); print("within task and arm, mean(opened - not opened):", round(obs, 3), "over", n, "cells")
random.seed(1); cells = collections.defaultdict(list)
for r in rows: cells[(r["arm"], r["task"])].append(r)
N, ge = 5000, 0
for _ in range(N):
    sh = []
    for c in cells.values():
        ops = [r["op"] for r in c]; random.shuffle(ops); sh += [dict(r, op=p) for r, p in zip(c, ops)]
    ge += within(sh)[0] >= obs
print("one-sided permutation p (opened better):", ge / N)
