# Preregistration: exploratory arms after the main study (draft, 2026-11-06)

**Status: draft for the user's review. No arm may run until this file is approved and its commit is tagged `prereg-arms`;
`official/vm/next-study-3.sh` refuses to start without that tag.** Designs, sources and worked examples:
`results/arm-designs.md`. These arms are exploratory. None changes, replaces or is pooled with the preregistered study
(`results/preregistration-v2.md`, amendments A1–A4), whose primary test stays as registered.

## What stays exactly as in the main study

Everything not listed under an arm's "changes" below:
- **Pipeline and settings:**
  - official `frontier-memory` commands (`generate-memory`, `run-tasks`, `score`, `bundle`) at commit `9af28c2f`, Harbor 0.24.0;
  - the 15 released tasks, 3 attempts each;
  - official per-task limits, timeout multiplier 1.0, one trial at a time;
  - the local model `qwen3.8:27b-mtp-q4_K_M` (context 262,144) behind the same relay, with requested effort `max`;
  - Hermes watchdog settings (D100) and the Docker-in-KVM guest;
  - the APEX judge (Claude Opus 5.5, verifier-side only, judge key never in an agent's environment);
  - the 6 h generation limit.
- **Set mechanics:** each arm's set script is derived from `official/vm/run-set-v1.sbatch` by exact replacements (`official/vm/derive_arm.py`). So resume, the rerun of no-reward trials, scoring, summary, key audit and the per-set audit are the same code as in the counted sets.
- **Checks after every set:** the same serving check (`check-serving.py`) and trial check, plus the arm check (`official/fm_local/arm_check.py`), which confirms from each trial's saved system prompt and the harness report that the arm was applied.

## Fidelity to the official protocol

Every arm uses the official commands and the documented `--harness module:Class` hook (`frontiermemory/docs/submitting-a-harness.md`). Each arm departs from `frontiermemory/docs/rules.md` in exactly the way listed here, and nowhere else.

| Arm | Within the official rules? | Departure |
|---|---|---|
| Generator | Yes: a custom memory-generation harness is what the rules allow ("The memory generation model is your choice") | Only the local model, as in the main study |
| C0/CM, K0/KM | Yes: the repo's fixed Codex and Claude Code task agents | Local model routing only (as Hermes in the main study). Codex gets a custom provider entry so its 300 s stream idle limit becomes 900 s, matching D100 |
| Read-first, scoped, cue, categorized | No: they change the fixed task agent's memory loading | That loading change is the treatment |
| Placebo | No: its memory does not come from a generation run | Control for content |
| Raw corpus, evidence | No: the agent reads corpus files instead of generated memory | That is the treatment; it gives the task agent the gated corpus |
| Recency a/b | No: the corpus digest differs from the release | A perturbed corpus copy is the treatment; no task trials |

Unlike a leaderboard submission (three runs, each with fresh memory), each arm is one 45-trial set on one memory: HM run 1's generation, or the arm's own single generation. So an arm's effect is measured for one memory. That limit is stated with every result.

## Arms, in run order (most promising first)

The comparator is "vs HM1" where the arm keeps run 1's memory content, and "vs A0" otherwise. The test is the main study's one-sided exact paired sign-flip over the 15 task-level pass-rate differences, with a 95 % interval by test inversion (`scripts/analyze_arms.py`). Every result is labelled exploratory. With 15 tasks, p < .05 needs at least 5 tasks moving one way and none the other; a null is not evidence of no effect.

| # | Arm | Changes | Comparator | Exploratory hypothesis (one-sided) |
|---|---|---|---|---|
| 1 | Placebo | Memory replaced by a size- and shape-matched placebo (`build_placebo.py`): same files and bytes, neutral names, public-domain text | vs HM1 and A0 | HM1 > placebo; placebo ≈ A0 |
| 2 | Read-first | HM plus one fixed sentence asking the agent to check its saved memory before starting | vs HM1 | Read-first > HM1; memory opened in more trials |
| 3 | Cue | Nothing shown at start. The fm-cue plugin appends a skill to a tool result when the call shares ≥ 2 non-generic terms with the skill's name and description, once per skill | vs HM1 | Cue > HM1 |
| 4 | Scoped (BM25) | Skills index holds the top 3 skills by Okapi BM25 (k1 1.2, b 0.75) between the task instruction and each SKILL.md; the full memory stays on disk | vs HM1 | Scoped > HM1 |
| 5 | Evidence | No generated memory; the task's related corpus runs (the coverage relation in `results/recency-check.json`) as files, with a one-line pointer; tasks with none get nothing | vs A0 (and HM1 for reference) | Evidence > A0 |
| 6 | Raw corpus | As evidence, but all 750 corpus runs | vs A0 (and HM1) | Raw > A0 |
| 7 | Generator | One fresh generation with three fixed, cited rules added to the official learn request (`generator_hermes.py`); HM delivery | vs A0 and HM1 | Generator > HM1 |
| 8–9 | C0, CM | Codex task agent, without and with HM1's memory; needs its own full gate first | CM vs C0 | CM > C0 |
| 10–11 | K0, KM | Claude Code task agent, likewise | KM vs K0 | KM > K0 |
| 12–13 | Recency a, b | Generation only, on a corpus copy with 7 injected stale/current fact pairs (`build_recency_corpus.py`); b swaps the two host files' names | Probe counts, a vs b | Current-only exceeds stale-only. Descriptive; no task trials, no test |
| 14 | Categorized | HM's memory skills indexed under three fixed categories (Hermes's own category headings) | vs HM1 | No direction claimed; likely null at about 10 skills |

Also reported (no new runs):
- **Dose, post hoc:** pass rate by how much memory was shown at start. E-none and cue show none; then scoped, HM1 and categorized, read-first, and E-all. Descriptive only.
- **Memory opened:** per arm (`scripts/memory_access.py`), and the cue plugin's activations and insertions.
- **Cross-harness differences** (C0 vs A0, K0 vs A0): descriptive only, with no test, because harness and loading rule are confounded.

## Gates and checks before counting

- **Effort probe, once, before any arm** (`official/vm/effort_probe.py`, run by `effort-check.sh`):
  - It sends the server the effort settings each harness sends and reports status and reasoning size.
  - It is reported, not a pass/fail condition, except that a refused Responses setting (Hermes "xhigh", Codex "max") is flagged.
- **Recommended first:** `STAGE=checks`, which runs only the effort probe, the harness gates and every end-to-end check (about a day), before the counted sets.
- **End-to-end check per arm:** one uncounted Word2Vec attempt (`E2E=1`) that must pass the arm check, the serving check and the trial check. For the cue arm it must show the plugin ran (`hook_calls ≥ 1`); the number of insertions is reported, not required.
- **Codex and Claude Code:** before C0/CM or K0/KM, a full uncounted gate as in gate 2 (`next-gate-harness.sh`): memory customer delivery plus one APEX task, then no-memory awilix-implicit to its full limit. It must show:
  - serving ok with keepalives;
  - every trial valid on its first round;
  - the judge completed;
  - the harness's own API path at the relay (`/v1/responses` or `/v1/messages`).
  - If Claude Code needs a translation proxy, stop and ask.
- **Model unavailability for Codex and Claude Code:** detected by the serving check (client closes, upstream errors, max-wait drops), because the Hermes text marker does not exist for them.
- **Placebo:** built once (`fm-mem-placebo`), and only used if every file matches its source's byte length and the skill counts match.
- **Generator:** the arm check confirms the generation used the arm's request.
- **Recency corpus:** used only with ≥ 6 facts and every file accounted for. The probe needs the generation to be valid.

## Rules carried over unchanged

- No-reward trials are rerun and not counted.
- An incomplete APEX judge is regraded before the set is accepted.
- No outcome-based exclusions, stopping or reordering.
- A failed generation (NO_VALID_MEMORY) is reported and its trials are not run.
- Any infrastructure stop keeps the finished sets and reports the shortfall.

## Order, time and compute

- **When it runs:** after the main study's job ends, in a new held job (`sbatch --dependency=singleton official/vm/run-arms.sbatch`), with the same 2 GPUs and node.
- **Estimated time:** about 13–14 h per 45-trial set, giving about 8 days for all arms. That is 12 task sets, 2 gates, 14 end-to-end checks, and 3 generations of up to 6 h.
- **Partial runs:** `ARMS="..."` runs a subset, still in this order.

## Not decided here

- Whether to run all arms or a subset, and whether any of them goes in the FORGE paper. Main-study results come first.
- The open main-study item, whether Ollama applies the requested effort, applies equally to every arm.

## Approval record

- Arms preregistration: **approved by the user, 2026-11-06** ("Do it.", with the order below).
- Order change before approval (main study amendment A5): the main study's none-shown exposure arm runs here, after
  read-first and before cue, as cue's control; its design and analysis are those of A2. All shown runs in the main job, after run 4.
- Runs in the main study's held allocation right after all shown (`next-study-2.sh` hands over), so the GPUs are never released between.
- `prereg-arms` tag: **created with this commit**.
- First arm trial: **not run**.

## Amendment B1 (2026-11-06, before any arm trial)

**Change (user decision):** the Codex (C0, CM) and Claude Code (K0, KM) arms, and their gates, move to a separate study on a
second GPU machine, run from a fresh clone of `main` with its own gate, its own no-memory control and its own HM1 generation.
They are not run on this cluster. Their designs, checks and tests are unchanged.

**Why:** the second machine is idle, while this cluster's job ends on Nov 17. The harness pairs compare within the harness
(CM vs C0, KM vs K0), so they don't need this cluster's numbers. The two machines' numbers are never compared: the hardware
differs.

**Order here:** placebo, read-first, exposure-none (A5), cue, scoped, evidence, raw corpus, generator, recency a/b, categorized.

## Amendment B2 (2026-11-06, before any arm trial)

**Changes (user decisions):**
- **Fast track:** placebo and read-first run first, right after the main study's run 3 and before its run 4 (main study amendment A6). Their designs, checks and comparators (vs HM1, and vs A0 for placebo) are unchanged.
- **Recency a/b moves to the second machine,** and runs there first after its gate. It is generation-only and needs no baseline, so it is self-contained there.

**Order here, then:** placebo, read-first; [main study: run 4, all-shown]; exposure-none, cue, scoped, evidence, raw corpus, generator, categorized.

## Amendment B3 (2026-11-06 16:30, during the placebo set, before its result)

**What happened:** D122. From 14:49 to about 15:57 Ollama served nothing (a runner hang); the server was restarted by hand.
The trial running then (placebo, APEX seat surplus) stalled for about 70 minutes.

**Rule, fixed now, before the placebo set's result:**
- Every placebo trial whose agent ran at any time in the window 2026-11-06 14:49:00 to 15:58:30 (Pacific) is an
  infrastructure casualty. It is set aside (kept, in `fm-tasks-arm-placebo.incident-d122/`) and rerun, **whatever its
  result**, through the same resume path as the official no-reward rerun.
- Serving faults inside that window, and only those, are excused (`check-serving.py --incidents
  official/vm/serving-incidents.json`). The rerun itself must pass the normal checks with nothing excused.
- The set's own end-of-set check stays strict, so it stops as designed; `official/vm/next-recover-d122.sh`, queued in the
  hold, then applies this rule and continues the study. Any other stop reason: it does nothing and the job holds.

## Amendment B4 (2026-11-08, before any scoped or categorized trial)

**Change (user decision, "Skip em"):** the **scoped** and **categorized** arms are not run. They are reported as not run, with this reason.

**Why, found before either arm ran (D134):** every Hermes generation we have (runs 1, 3, 4 and the second gate) exports exactly one skill,
one SKILL.md plus 5 to 12 supporting files. Scoped keeps the top 3 skills for each task, which is that one skill, the same as ordinary
memory; categorized files the skills under category folders, which is that one skill in one folder. On the real run 1 memory both builders
produce one skill. Neither arm can differ from the HM run 1 arm, so running them would cost about 14 hours each and test nothing.
This is a design fact about the memory format, known without any result of either arm.

**Order now:** placebo, read-first, none-shown, cue, evidence, raw, generator (the rest of A5/B2 is unchanged). The free job time is left unused.
The preregistered test, the secondary outcomes and every other arm's rules are unchanged.

## Amendment B5 (2026-11-09 16:40, during the none-shown set, before any trial of cue, evidence, raw, generator, K0, KM or recency)

**1. All-shown stalls (D136), the B3 rule applied again.** From 23:44 on Nov 8, Ollama's request layer repeatedly held
calls for 15 to 30 minutes with the model idle. Nine windows, built from the relay's own stall records
(`official/vm/serving-incidents-d136.json`), cover every abort, 5xx, max-wait drop and superseded call of the set; outside
them the set's serving check passes (0 aborts, 17 of 17 closes at an agent's end). Every all-shown trial whose agent ran in
a window, 10 trials, is an infrastructure casualty: set aside (kept, in `fm-tasks-exposure-all.incident-d136/`) and rerun,
**whatever its result**, through the same resume path as the official no-reward rerun. The rerun must pass the normal checks
with nothing excused. The set-aside list is fixed now: automationbench sales partnership, awilix explicit, awilix
implicit, Word2Vec, cattrs, cookie store, customer delivery, DAPT, EnterpriseOps CSM, EnterpriseOps teams (all 10 ended
AgentTimeoutError; 0 of them passed).

**2. Arms not run (user decision, Nov 9, on the time left and each arm's value; no result of any of them exists).**
- **cue** is not run: read-first already raised memory opens from 15 to 27 of 45 with no score change, so a cue that
  delivers the same skill earlier tests a lever already shown to be weak here.
- **raw** is not run: 750 corpus files (235 MB) are far beyond what the 27B agent can search in its time limits; evidence
  (the related past runs given directly) tests the same question in a usable form.
- **K0, KM (Claude Code) and recency a/b** are not run on either machine. On the second machine the Claude Code gate failed
  twice: each time a model call was still in flight when a trial hit its 90-minute agent limit (start + duration of each
  close lands 12 to 40 s after the agent's timeout). That is the model's speed against Claude Code's limits, so a gate here
  would fail the same way. The second machine is released for a separate exploratory project.

**Order now:** [none-shown, running]; then the all-shown rerun (item 1); then **evidence**, **generator**. Then the job is
released. Nothing else changes: designs, checks, comparators, and the primary test (done) are unaffected.
