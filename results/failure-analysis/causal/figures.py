"""Draw the figures for the requirement-level report from requirement-analysis.json.

Usage: python3 figures.py requirement-analysis.json OUT_DIR
"""
import json, sys, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df", "#fcfcfb"
BLUE, ORANGE, AQUA, VIOLET, RED = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6", "#e34948"
SEQ = LinearSegmentedColormap.from_list("seq", ["#f0efec", "#cde2fb", "#86b6ef", "#2a78d6", "#104281"])
ARM_ORDER = ["control", "placebo", "noneshown", "run1", "readfirst", "allshown", "blend", "run3", "run4", "evidence"]
ARM_LABEL = {"control": "No memory", "placebo": "Placebo\n(novel text)", "noneshown": "Run 1 notes\nnot advertised",
             "run1": "Run 1 notes\nindexed", "readfirst": "Run 1 notes\n+ read first", "allshown": "Run 1 notes\nin prompt",
             "blend": "Run 1 notes\nin task text", "run3": "Run 3 notes\nindexed", "run4": "Run 4 notes\nindexed",
             "evidence": "Raw earlier\nruns"}
TASK_LABEL = {
    "apex-brightpath-market-share": "Market share", "apex-brightpath-seat-surplus": "Seat surplus",
    "apex-eurogrid-curtailment": "Eurogrid", "automationbench-marketing-conten": "Marketing gap",
    "automationbench-sales-chatgpt-pr": "ChatGPT proposal", "automationbench-sales-partnershi": "Partnership",
    "awilix-release-tier-explicit": "Awilix explicit", "awilix-release-tier-implicit": "Awilix implicit",
    "build-word2vec-pipeline": "Word2Vec", "cattrs-compositional-changelog": "cattrs",
    "cookie-store-compositional-chang": "Cookie store", "customer-delivery-contextual-pre": "Customer delivery",
    "dapt-intrusion-detection-workflo": "DAPT", "enterpriseops-csm-26d1b04a": "CSM", "enterpriseops-teams-2725d17f": "Teams"}


def style(ax):
    ax.set_facecolor(SURF)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=INK2, length=0, labelsize=8)


def frac(s):
    a, b = s.split("/")
    return int(a), int(b)


def heat(ax, rows, cols, cells, row_labels, col_labels):
    import numpy as np
    m = np.full((len(rows), len(cols)), np.nan)
    for i, r in enumerate(rows):
        for j, c in enumerate(cols):
            a, b = cells[i][j]
            if b:
                m[i, j] = a / b
    ax.imshow(m, cmap=SEQ, vmin=0, vmax=1, aspect="auto")
    for i in range(len(rows)):
        for j in range(len(cols)):
            a, b = cells[i][j]
            v = a / b if b else 0
            ax.text(j, i, f"{a}/{b}" if b else "–", ha="center", va="center", fontsize=7,
                    color="white" if v > 0.6 else INK)
    ax.set_xticks(range(len(cols)), col_labels, fontsize=7)
    ax.set_yticks(range(len(rows)), row_labels, fontsize=8)
    ax.xaxis.tick_top()
    ax.set_xticks([x - 0.5 for x in range(1, len(cols))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(rows))], minor=True)
    ax.grid(which="minor", color=SURF, linewidth=2)
    ax.tick_params(which="minor", length=0)
    style(ax)


def main(src, out):
    os.makedirs(out, exist_ok=True)
    d = json.load(open(src))

    tasks = sorted(d["strict_passes"], key=lambda t: -sum(d["strict_passes"][t].values()))
    cells = [[(d["strict_passes"][t].get(a, 0), 3) for a in ARM_ORDER] for t in tasks]
    fig, ax = plt.subplots(figsize=(10, 6.4), facecolor=SURF)
    heat(ax, tasks, ARM_ORDER, cells, [TASK_LABEL[t] for t in tasks], [ARM_LABEL[a] for a in ARM_ORDER])
    tot = [sum(d["strict_passes"][t].get(a, 0) for t in tasks) for a in ARM_ORDER]
    for j, v in enumerate(tot):
        ax.text(j, len(tasks) - 0.1 + 0.55, f"{v}/45", ha="center", va="top", fontsize=8, color=INK, fontweight="bold")
    ax.set_ylim(len(tasks) + 0.4, -0.5)
    ax.set_title("Strict passes by task and arm (out of 3 attempts; column totals out of 45)", loc="left", fontsize=10, color=INK, pad=42)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig1-task-arm-heatmap.png"), dpi=160)
    plt.close(fig)

    import re as _re
    reqs = [r for r in d["requirements"] if r["status"] in ("contested", "never_met")]
    reqs.sort(key=lambda r: (r["task"], int((_re.search(r"R(\d+)", r["id"]) or [0, 0])[1])))
    cells = [[frac(r["by_arm"][a]) for a in ARM_ORDER] for r in reqs]
    labels = []
    for r in reqs:
        mem = r["memory"]["run1"]
        tag = {"yes": "●", "partial": "◐", "no": "○"}[mem]
        labels.append(f"{TASK_LABEL[r['task']]} · {r['id'].split('_')[0].split('-')[0]} {r['id'][len(r['id'].split('_')[0].split('-')[0]) + 1:][:30].replace('_', ' ').replace('-', ' ')}  {tag} {r['prompt'][:4]}")
    fig, ax = plt.subplots(figsize=(11, 0.26 * len(reqs) + 1.6), facecolor=SURF)
    heat(ax, reqs, ARM_ORDER, cells, labels, [ARM_LABEL[a] for a in ARM_ORDER])
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.9 / (0.26 * len(reqs) + 1.6)))
    fig.text(0.01, 0.995, "Each requirement that some trial failed: trials that met it, by arm", fontsize=10, color=INK, va="top")
    fig.text(0.01, 0.995 - 0.3 / (0.26 * len(reqs) + 1.6), "● run 1 notes cover it · ◐ partly · ○ not at all.   expl = the prompt states it · deri = derivable from the task's own data or tools · abse = neither", fontsize=8, color=INK2, va="top")
    fig.savefig(os.path.join(out, "fig2-requirement-arm-heatmap.png"), dpi=160)
    plt.close(fig)

    ex = d["exposure_ladder"]
    ladder = ["control", "placebo", "noneshown", "run1", "readfirst", "allshown"]
    fig, ax = plt.subplots(figsize=(8.5, 4.4), facecolor=SURF)
    for key, color, name in (("run1_yes", BLUE, "Run 1's notes cover it"),
                             ("run1_partial", VIOLET, "Run 1's notes partly cover it"),
                             ("run1_no", ORANGE, "Run 1's notes do not cover it")):
        if key not in ex:
            continue
        e = ex[key]
        ys = [e["rates"][a]["rate"] for a in ladder]
        p = e["trend_p_one_sided_trial_perm"]
        ax.plot(range(len(ladder)), ys, color=color, linewidth=2, marker="o", markersize=7,
                markeredgecolor=SURF, markeredgewidth=2,
                label=f"{name}: {e['requirements']} requirements, {len(e['tasks'])} tasks; trend {'p<0.001' if p < 0.001 else 'p=' + format(p, '.2f')}")
        ax.text(len(ladder) - 1 + 0.12, ys[-1] + {"run1_yes": 0, "run1_partial": 0.025, "run1_no": -0.025}[key], f"{ys[-1]:.2f}", va="center", fontsize=8, color=INK2)
    ax.set_xticks(range(len(ladder)), [ARM_LABEL[a] for a in ladder], fontsize=7.5)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Share of trial-requirements met", fontsize=8.5, color=INK2)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    style(ax)
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    ax.set_title("Requirements some trial failed, by how run 1's notes reached the agent", loc="left", fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig3-exposure-ladder.png"), dpi=160)
    plt.close(fig)

    ct = d["content_test"]
    fig, ax = plt.subplots(figsize=(7.5, 2.8), facecolor=SURF)
    rows = [("yes", "Arm's notes cover the requirement"), ("partial", "Notes partly cover it"), ("no", "Notes do not cover it")]
    for i, (k, name) in enumerate(rows):
        if k not in ct:
            continue
        c = ct[k]
        lo, hi = c["ci95_task_boot"]
        p = c["p_one_sided_trial_perm"]
        ax.plot([lo, hi], [i, i], color=MUTED, linewidth=2, solid_capstyle="round")
        ax.plot([c["mean_diff"]], [i], "o", color=BLUE, markersize=8, markeredgecolor=SURF, markeredgewidth=2)
        ax.text(1.08, i, f"{c['mean_diff']:+.2f}   {'p<0.001' if p < 0.001 else 'p=' + format(p, '.3f')}   {c['units']} req×arm, {len(c['tasks'])} tasks",
                va="center", fontsize=7.5, color=INK2, transform=ax.get_yaxis_transform())
    ax.axvline(0, color=INK2, linewidth=1)
    ax.set_yticks(range(len(rows)), [n for _, n in rows], fontsize=8)
    ax.set_xlim(-1, 1)
    ax.invert_yaxis()
    ax.set_xlabel("Share of trials meeting the requirement, memory arm minus no-memory control", fontsize=8, color=INK2)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    style(ax)
    ax.set_title("Arm minus control, by whether the arm's notes cover the requirement\n(dot: mean; line: 95% interval resampling tasks; p: permuting whole trials within task)", loc="left", fontsize=9, color=INK)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig4-content-test.png"), dpi=160, bbox_inches="tight")
    plt.close(fig)

    import textwrap
    cas = d["cascade"]
    names = {"absent": "Missed a requirement whose information was in neither the task nor this arm's notes (or in unread raw records)",
             "partial": "Of the rest: missed a requirement this arm's notes only partly covered",
             "notes_only": "Of the rest: missed a requirement only this arm's notes fully covered",
             "available_only": "The rest: every missed requirement was stated in, or derivable from, the task"}
    total = sum(c["taken"] for c in cas)
    fig, ax = plt.subplots(figsize=(10, 4.2), facecolor=SURF)
    left = total
    ax.barh(0, total, color=MUTED, height=0.6)
    ax.text(total + 4, 0, f"{total}", va="center", fontsize=8, color=INK)
    for y, (c, col) in enumerate(zip(cas, [ORANGE, VIOLET, BLUE, AQUA]), start=1):
        left -= c["taken"]
        ax.barh(y, max(c["taken"], 0.8), left=left, color=col, height=0.6)
        ax.text(left + c["taken"] + 4, y, f"{c['taken']}   (match in any order: {c['match_any_order']})", va="center", fontsize=7.5, color=INK2)
    labels = ["All failed trials"] + [names[c["step"]] for c in cas]
    ax.set_yticks(range(len(labels)), [textwrap.fill(l, 52) for l in labels], fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlim(0, total * 1.45)
    ax.set_xticks([])
    style(ax)
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.text(0.01, 0.97, "Failed trials by where the information for their missed requirements was", fontsize=10, color=INK, va="top")
    fig.text(0.01, 0.92, "Each row takes the failed trials still left that match it; the count in brackets ignores the order.", fontsize=8, color=INK2, va="top")
    fig.savefig(os.path.join(out, "fig5-failure-cascade.png"), dpi=160)
    plt.close(fig)
    print("figures written to", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
