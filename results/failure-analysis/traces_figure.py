"""Figure 5 for REPORT.md: failures by cause per arm after the trace pass. Reads traces/traces-all.json."""
import json, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
H = os.path.dirname(os.path.abspath(__file__))
ALIAS = {"arm-readfirst":"readfirst","exposure-all":"allshown","exposure-none":"noneshown","arm-blend":"blend","arm-placebo":"placebo","arm-evidence":"evidence"}
rows = json.load(open(os.path.join(H, "traces", "traces-all.json")))
for r in rows: r["arm"] = ALIAS.get(r["arm"], r["arm"])
ARMS = [("control","Control"),("run1","Run 1"),("run3","Run 3"),("run4","Run 4"),("placebo","Placebo"),("readfirst","Read-first"),
        ("allshown","All shown"),("noneshown","None shown"),("evidence","Evidence"),("blend","Blend")]
G = {"A1":"Grader caps the score","B1":"No source or nothing given","B2":"No source or nothing given","B7":"Memory not shown (by design)",
     "B3":"Memory lacked the point or was vague","B3d":"Memory lacked the point or was vague","B4":"Memory lacked the point or was vague",
     "C1":"Shown, never opened","C2":"Opened or used, did not help","C4":"Opened or used, did not help","C5":"Opened or used, did not help",
     "C6":"Opened or used, did not help","A3":"Task beyond the model or hidden convention","A7":"Task beyond the model or hidden convention"}
ORDER = ["Grader caps the score","No source or nothing given","Memory not shown (by design)","Memory lacked the point or was vague",
         "Shown, never opened","Opened or used, did not help","Task beyond the model or hidden convention"]
COL = dict(zip(ORDER, ["#4c78a8","#72b7b2","#9ecae9","#b279a2","#e45756","#54a24b","#f58518"]))
plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
fig, ax = plt.subplots(figsize=(9,4.8)); bottom = np.zeros(len(ARMS))
for g in ORDER:
    v = np.array([sum(1 for r in rows if r["arm"]==a and G[r["new_primary_bucket"]]==g) for a,_ in ARMS])
    ax.bar([n for _,n in ARMS], v, bottom=bottom, color=COL[g], label=g, edgecolor="white", linewidth=.6); bottom += v
for i,t in enumerate(bottom): ax.text(i, t+.6, int(t), ha="center", fontsize=9)
ax.set_ylabel("Failed trials (of 45)"); ax.set_ylim(0,50); plt.xticks(rotation=30, ha="right")
ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(.5,-.28), ncol=2)
ax.set_title("What the failures were attributed to after reading the trajectories")
plt.tight_layout(); plt.savefig(os.path.join(H,"figures","fig5-failure-causes-after-traces.png"), dpi=170); plt.close()
import collections
print(collections.Counter(G[r["new_primary_bucket"]] for r in rows))
