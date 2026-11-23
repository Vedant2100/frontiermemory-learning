"""Draw the stage figures from stages.json.

Usage: python3 stage_figures.py stages.json OUT_DIR aggregation.json [successes.json]
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


def main(src, out, agg_src, succ_src=None):
    d = json.load(open(src))
    agg = json.load(open(agg_src))
    os.makedirs(out, exist_ok=True)

    per = agg["generation_stage_distinct"]
    gens = [("run1", "Run 1 writer"), ("run3", "Run 3 writer"), ("run4", "Run 4 writer")]
    panels = [("scored_not_in_task", "19 failed requirements the task does not give"), ("scored_requirements", "All 72 scored requirements")]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), facecolor=SURF, gridspec_kw={"width_ratios": [1, 1.6]})
    for ax, (key, title) in zip(axes, panels):
        total = sum(per["run1"][key].values())
        for y, (g, name) in enumerate(gens):
            left = 0
            for k, _, col in UP:
                v = per[g][key].get(k, 0)
                if v:
                    ax.barh(y, v, left=left, color=col, height=0.62, edgecolor=SURF, linewidth=2)
                    if v >= (2 if total < 30 else 5):
                        ax.text(left + v / 2, y, str(v), ha="center", va="center", fontsize=8, color="white")
                left += v
        ax.set_yticks(range(len(gens)), [n for _, n in gens] if ax is axes[0] else [""] * 3, fontsize=8.5)
        ax.invert_yaxis()
        ax.set_xlim(0, total)
        ax.set_xticks(list(range(0, total, 5 if total < 30 else 10)) + [total])
        ax.set_title(title, fontsize=8.5, color=INK2, loc="left")
        ax.xaxis.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        style(ax)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in UP]
    axes[0].legend(handles, [l for _, l, _ in UP], ncol=3, fontsize=7.5, frameon=False, loc="upper left", bbox_to_anchor=(0, -0.14))
    fig.text(0.01, 0.97, "Where the information for each requirement stopped, by generation of notes", fontsize=10, color=INK, va="top")
    fig.text(0.01, 0.91, "One unit per distinct requirement; traced through the earlier-run corpus and each note-writer's session", fontsize=8, color=INK2, va="top")
    fig.tight_layout(rect=(0, 0.04, 1, 0.86))
    fig.subplots_adjust(wspace=0.06)
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
    bm = d["by_prompt_mode"]["blind"]
    by_arm = bm["trial_requirements_by_arm_and_stage"]
    pa = bm["per_arm"]
    arm_names = [("control", "Control"), ("placebo", "Placebo notes"), ("evidence", "Raw records"), ("blend", "Blend"),
                 ("run1", "Run 1 notes"), ("run3", "Run 3 notes"), ("run4", "Run 4 notes"),
                 ("readfirst", "Read-first"), ("allshown", "All shown"), ("noneshown", "None shown")]
    segs = [("In the task; agent missed it", AQUA, ("in_task_missed",)),
            ("No notes in this arm", GRID, ("no_memory_arm", "raw_records_arm", "blend_arm")),
            ("No earlier run holds it", MUTED, ("experience_missing",)),
            ("Never reached the writer", ORANGE, ("writer_never_saw",)),
            ("Writer saw it; notes hold part, none, or a misleading rule", VIOLET, ("writer_saw_partial", "writer_saw_dropped", "writer_misled")),
            ("In the notes; not shown or not opened", RED, ("not_shown_by_design", "not_opened")),
            ("In the notes; opened, still failed", BLUE, ("used_still_failed",))]
    fig, ax = plt.subplots(figsize=(10, 4.6), facecolor=SURF)
    xmax = max(sum(v.values()) for v in by_arm.values())
    for y, (a, name) in enumerate(arm_names):
        left = 0
        for _, col, keys in segs:
            v = sum(by_arm[a].get(k, 0) for k in keys)
            if v:
                ax.barh(y, v, left=left, color=col, height=0.62, edgecolor=SURF, linewidth=2)
                if v >= 8:
                    ax.text(left + v / 2, y, str(v), ha="center", va="center", fontsize=7.5, color=INK if col == GRID else "white")
            left += v
        ax.text(left + 1.5, y, f"{pa[a]['failed_trials']}/{pa[a]['trials']} trials failed", va="center", fontsize=7.5, color=INK2)
    ax.set_yticks(range(len(arm_names)), [n for _, n in arm_names], fontsize=8.5)
    ax.axhline(3.5, color=INK2, linewidth=0.6)
    ax.invert_yaxis()
    ax.set_xlim(0, xmax * 1.28)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    style(ax)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, c, _ in segs]
    ax.legend(handles, [l for l, _, _ in segs], ncol=3, fontsize=7.5, frameon=False, loc="upper left", bbox_to_anchor=(0, -0.08))
    fig.text(0.01, 0.97, "Where each arm's failed requirements broke", fontsize=10, color=INK, va="top")
    fig.text(0.01, 0.92, "Unit: one requirement failed in one trial. 'In the task' from outcome-blind labels. Arms above the line had no generated notes.", fontsize=8, color=INK2, va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.89))
    fig.savefig(os.path.join(out, "fig8-stages-by-arm.png"), dpi=160)
    plt.close(fig)
    if succ_src:
        sc = json.load(open(succ_src))["passes_by_arm"]
        classes = [("task_gave_everything", "Task gave every requirement", AQUA),
                   ("outside_info_all_from_notes_read", "Needed outside information; read the covering notes file for all of it", BLUE),
                   ("outside_info_partly_from_notes_read", "Needed outside information; read the covering notes file for part of it", VIOLET),
                   ("raw_records_opened", "Needed outside information; opened raw records", ORANGE),
                   ("outside_info_met_without_reading_a_covering_source", "Needed outside information; no covering source read", MUTED)]
        fig, ax = plt.subplots(figsize=(10, 4.4), facecolor=SURF)
        for y, (a, name) in enumerate(arm_names):
            left = 0
            for k, _, col in classes:
                v = sc[a]["by_class"].get(k, 0)
                if v:
                    ax.barh(y, v, left=left, color=col, height=0.62, edgecolor=SURF, linewidth=2)
                    if v >= 2:
                        ax.text(left + v / 2, y, str(v), ha="center", va="center", fontsize=7.5, color="white")
                left += v
            ax.text(left + 0.15, y, f"{sc[a]['passes']}/{sc[a]['of']}", va="center", fontsize=7.5, color=INK2)
        ax.set_yticks(range(len(arm_names)), [n for _, n in arm_names], fontsize=8.5)
        ax.axhline(3.5, color=INK2, linewidth=0.6)
        ax.invert_yaxis()
        ax.set_xlim(0, 11)
        ax.set_xticks(range(0, 11, 2))
        ax.xaxis.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        style(ax)
        handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in classes]
        ax.legend(handles, [l for _, l, _ in classes], ncol=2, fontsize=7.5, frameon=False, loc="upper left", bbox_to_anchor=(0, -0.08))
        fig.text(0.01, 0.97, "Where each arm's passing trials got their information", fontsize=10, color=INK, va="top")
        fig.text(0.01, 0.92, "Passes of 45 trials per arm. 'Outside information': requirements the task does not give (outcome-blind labels). Arms above the line had no generated notes.", fontsize=8, color=INK2, va="top")
        fig.tight_layout(rect=(0, 0, 1, 0.89))
        fig.savefig(os.path.join(out, "fig9-passes-by-arm.png"), dpi=160)
        plt.close(fig)
    print("stage figures written to", out)


if __name__ == "__main__":
    main(*sys.argv[1:5])
