"""Draw the stage figures from stages.json.

Usage: python3 stage_figures.py stages.json OUT_DIR
"""
import json, sys, os, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from figures import INK, INK2, MUTED, GRID, SURF, BLUE, ORANGE, AQUA, VIOLET, RED, style

UP = [("experience_missing", "No earlier run holds it", MUTED),
      ("writer_never_saw", "In earlier runs, never reached the writer", ORANGE),
      ("writer_misled", "Notes carry a misleading rule", "#7a2e2e"),
      ("writer_saw_dropped", "Writer saw it, notes lack it", RED),
      ("writer_saw_partial", "Writer saw it, notes hold part", VIOLET),
      ("in_notes", "In the notes", BLUE)]


def main(src, out):
    d = json.load(open(src))
    os.makedirs(out, exist_ok=True)

    per = d["all_failed_trial_requirements_by_upstream_stage_per_generation"]
    gens = [("run1", "Run 1 writer"), ("run3", "Run 3 writer"), ("run4", "Run 4 writer")]
    total = sum(per["run1"].values())
    fig, ax = plt.subplots(figsize=(10, 3.4), facecolor=SURF)
    for y, (g, name) in enumerate(gens):
        left = 0
        for k, _, col in UP:
            v = per[g].get(k, 0)
            if v:
                ax.barh(y, v, left=left, color=col, height=0.62, edgecolor=SURF, linewidth=2)
                if v >= 25:
                    ax.text(left + v / 2, y, str(v), ha="center", va="center", fontsize=8, color="white")
            left += v
    ax.set_yticks(range(len(gens)), [n for _, n in gens], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0, total)
    ax.set_xticks([0, 200, 400, 600, total])
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    style(ax)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in UP]
    ax.legend(handles, [l for _, l, _ in UP], ncol=3, fontsize=7.5, frameon=False, loc="upper left", bbox_to_anchor=(0, -0.12))
    fig.text(0.01, 0.97, f"Where the information for each failed requirement stopped, all {total} failed trial-requirements", fontsize=10, color=INK, va="top")
    fig.text(0.01, 0.91, "Traced through the earlier-run corpus and each note-writer's session; same failures, read against each generation of notes", fontsize=8, color=INK2, va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.savefig(os.path.join(out, "fig6-where-information-stopped.png"), dpi=160)
    plt.close(fig)

    s = d["by_prompt_mode"]["blind"]["trial_requirements_by_stage"]
    notes_keys = ("experience_missing", "writer_never_saw", "writer_misled", "writer_saw_dropped", "writer_saw_partial", "not_shown_by_design", "not_opened", "used_still_failed")
    rows = [
        ("Failed trial-requirements, all arms", d["failed_trial_requirements"], MUTED, 0),
        ("Information was in the task (blind labels): agent missed it", s.get("in_task_missed", 0), AQUA, 1),
        ("Arms without generated notes (control, placebo, raw records, blend)", s.get("no_memory_arm", 0) + s.get("raw_records_arm", 0) + s.get("blend_arm", 0), GRID, 1),
        ("Notes arms, information not in the task", sum(s.get(k, 0) for k in notes_keys), MUTED, 1),
        ("No earlier run holds it", s.get("experience_missing", 0), MUTED, 2),
        ("Never reached the writer", s.get("writer_never_saw", 0), ORANGE, 2),
        ("Writer saw it; notes hold part, none, or a misleading rule", s.get("writer_saw_partial", 0) + s.get("writer_saw_dropped", 0) + s.get("writer_misled", 0), VIOLET, 2),
        ("In the notes; none-shown arm, agent did not find them", s.get("not_shown_by_design", 0), RED, 2),
        ("In the notes and listed; agent did not open the file", s.get("not_opened", 0), RED, 2),
        ("In the notes; agent opened the file or had it pasted in", s.get("used_still_failed", 0), BLUE, 2),
    ]
    fig, ax = plt.subplots(figsize=(10, 4.9), facecolor=SURF)
    for y, (label, v, col, lvl) in enumerate(rows):
        if v:
            ax.barh(y, v, color=col, height=0.62)
        ax.text(v + 6, y, str(v), va="center", fontsize=8, color=INK)
    ax.set_yticks(range(len(rows)), [({0: "", 1: "", 2: "\u25b8 "}[r[3]]) + textwrap.fill(r[0], 70) for r in rows], fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlim(0, d["failed_trial_requirements"] * 1.12)
    ax.set_xticks([])
    style(ax)
    fig.text(0.01, 0.97, "Following each failed requirement from earlier runs to the answer", fontsize=10, color=INK, va="top")
    fig.text(0.01, 0.92, "Rows 2 to 4 split the first row; rows marked \u25b8 split row 4. Unit: one requirement failed in one trial. 'In the task' from outcome-blind labels.", fontsize=8, color=INK2, va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(os.path.join(out, "fig7-stage-funnel.png"), dpi=160)
    plt.close(fig)
    print("stage figures written to", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
