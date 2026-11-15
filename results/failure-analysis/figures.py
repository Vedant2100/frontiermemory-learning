"""Figures for REPORT.md. Reads all-failures.json and results/official/*.jsonl; writes figures/*.png."""
import json, collections, statistics, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); O = os.path.join(H, "..", "official"); F = os.path.join(H, "figures")
rows = json.load(open(os.path.join(H, "all-failures.json")))
SETS = [("control","control","Control"),("run1","run1","Run 1"),("run3","run3","Run 3"),("run4","run4","Run 4"),
        ("placebo","arm-placebo","Placebo"),("arm-readfirst","arm-readfirst","Read-first"),("exposure-all","exposure-all","All shown"),
        ("exposure-none","exposure-none","None shown"),("evidence","arm-evidence","Evidence"),("arm-blend","arm-blend","Blend")]
def summ(s): return [json.loads(l) for l in open(os.path.join(O, f"summary-fm-tasks-{s}.jsonl"))]
GROUP = {"A1":"Grader caps the score","B1":"No source or nothing given","B2":"No source or nothing given","B7":"Memory not shown (by design)",
         "A3":"Task beyond the model (inferred)","A7":"Task beyond the model (inferred)","C6":"Memory used, still failed","D1":"Cannot tell from retained logs"}
ORDER = ["Grader caps the score","No source or nothing given","Memory not shown (by design)","Task beyond the model (inferred)","Memory used, still failed","Cannot tell from retained logs"]
COL = {"Grader caps the score":"#4c78a8","No source or nothing given":"#72b7b2","Memory not shown (by design)":"#9ecae9",
       "Task beyond the model (inferred)":"#f58518","Memory used, still failed":"#54a24b","Cannot tell from retained logs":"#bab0ac"}
plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})

# Fig 1: failures by cause group per arm
fig, ax = plt.subplots(figsize=(9,4.6)); bottom = np.zeros(len(SETS))
for g in ORDER:
    v = np.array([sum(1 for r in rows if r["arm"]==a and GROUP[r["primary_bucket"][:2]]==g) for a,_,_ in SETS])
    ax.bar([n for *_,n in SETS], v, bottom=bottom, color=COL[g], label=g, edgecolor="white", linewidth=.6); bottom += v
for i,t in enumerate(bottom): ax.text(i, t+.6, int(t), ha="center", fontsize=9)
ax.set_ylabel("Failed trials (of 45)"); ax.set_ylim(0,50); plt.xticks(rotation=30, ha="right")
ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(.5,-.28), ncol=3)
ax.set_title("What the failures were attributed to, by arm")
plt.tight_layout(); plt.savefig(os.path.join(F,"fig1-failure-causes-by-arm.png"), dpi=170); plt.close()

# Fig 2: pass count heatmap (task x arm)
tasks = sorted({r["task"].split("/")[-1] for r in summ("control")})
M = np.zeros((len(tasks), len(SETS)))
for j,(_,s,_) in enumerate(SETS):
    for r in summ(s):
        M[tasks.index(r["task"].split("/")[-1]), j] += r["passed"]
order = np.argsort(M.sum(1))
fig, ax = plt.subplots(figsize=(8.6,5.6)); im = ax.imshow(M[order], cmap="Blues", vmin=0, vmax=3, aspect="auto")
ax.set_xticks(range(len(SETS))); ax.set_xticklabels([n for *_,n in SETS], rotation=35, ha="right")
ax.set_yticks(range(len(tasks))); ax.set_yticklabels([tasks[i][:42] for i in order], fontsize=8)
for i in range(len(tasks)):
    for j in range(len(SETS)):
        v = int(M[order][i,j]); ax.text(j,i,v,ha="center",va="center",color="white" if v>=2 else "#333",fontsize=8)
ax.set_title("Passes out of 3 attempts, per task and arm"); plt.colorbar(im, ax=ax, fraction=.03, label="passes")
for s in ("top","right","left","bottom"): ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig(os.path.join(F,"fig2-passes-by-task-and-arm.png"), dpi=170); plt.close()

# Fig 3: memory opened, run 1 vs read-first, failed vs passed
def acc(name):
    return {json.loads(l)["trial"]: json.loads(l) for l in open(os.path.join(O, f"memory-access-{name}.jsonl"))}
res = {}
for name in ("run1","readfirst"):
    a = acc(name); passed = {r["trial"] for r in summ("run1" if name=="run1" else "arm-readfirst") if r["passed"]}
    f = [t for t in a if t not in passed]; p = [t for t in a if t in passed]
    res[name] = (100*np.mean([a[t]["opened"] for t in f]), 100*np.mean([a[t]["opened"] for t in p]), 100*np.mean([a[t]["opened"] for t in a]), len(f), len(p))
fig, ax = plt.subplots(figsize=(6.6,4)); w=.26; x=np.arange(2)
for k,(lab,c) in enumerate([("Failed trials","#f58518"),("Passed trials","#4c78a8"),("All trials","#888")]):
    vals=[res["run1"][k],res["readfirst"][k]]; ax.bar(x+(k-1)*w, vals, w, label=lab, color=c)
    for xi,v in zip(x+(k-1)*w, vals): ax.text(xi, v+1.5, f"{v:.0f}%", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(["Run 1\n(standard)","Read-first\n(nudge in prompt)"]); ax.set_ylabel("Trials where the agent opened memory (%)"); ax.set_ylim(0,80)
ax.legend(frameon=False); ax.set_title("The nudge doubled opens; strict passes did not move")
plt.tight_layout(); plt.savefig(os.path.join(F,"fig3-memory-opened.png"), dpi=170); plt.close()
json.dump(res, open(os.path.join(F,"fig3-values.json"),"w"))

# Fig 4: partial credit of failed trials, control vs memory arms, per task
P = collections.defaultdict(lambda: collections.defaultdict(list))
for s_key,s,_ in SETS:
    for l in open(os.path.join(O, f"partial-credit-fm-tasks-{s}.jsonl")):
        r = json.loads(l)
        if r["strict"] < 1: P[r["trial"].rsplit("__",1)[0]][("c" if s=="control" else "m")].append(r["partial"])
names = sorted(P, key=lambda t: statistics.mean(P[t]["c"] or [0]))
fig, ax = plt.subplots(figsize=(8,5.6))
for i,t in enumerate(names):
    for kind,col,dy in (("m","#4c78a8",.12),("c","#f58518",-.12)):
        v = P[t][kind]; ax.scatter(v, [i+dy]*len(v), s=14, color=col, alpha=.55, linewidths=0)
ax.set_yticks(range(len(names))); ax.set_yticklabels([n[:42] for n in names], fontsize=8); ax.set_xlabel("Share of checks passed in a failed trial")
ax.scatter([],[],color="#f58518",label="Control (no memory)"); ax.scatter([],[],color="#4c78a8",label="The other nine arms pooled"); ax.legend(frameon=False, loc="lower left")
ax.set_xlim(-.03,1.03); ax.grid(axis="x", color="#eee"); ax.set_title("How close the failed trials came")
plt.tight_layout(); plt.savefig(os.path.join(F,"fig4-partial-credit-failed.png"), dpi=170); plt.close()
print(res)
