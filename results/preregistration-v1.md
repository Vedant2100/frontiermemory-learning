# Preregistration v1: memory construction and governance on FrontierMemory (confirmatory matrix)

Status: DRAFT. It is frozen when committed with the tag `prereg-v1`, before any confirmatory trial runs. Any later change is a dated amendment at the bottom.
Target: FORGE 2027 Data & Benchmarking track. Exploratory results so far (`ab-v5-results.md`, the ladder) are labeled exploratory and are **not** pooled with this matrix.

## 0. Principle: every memory arm is built by software, not by a person

No arm involves a researcher choosing, editing, or filtering evidence or lessons. Each arm is fully specified by the following, all committed before trials:
- the frozen corpus (`joint-674-v1.0`, digest `c7d31214…`);
- the official instruction (`dream_task/instruction.md`, sha `a96e69af…`);
- a model and its settings;
- code with fixed parameters and seeds.

No construction step sees the target tasks, their instructions, verifiers, or solutions, or any task outcome. The earlier hand-picked slices (v2, v3, v4) were chosen by target-task keyword. They stay in the exploratory record only.

## 1. Arms

| Arm | Construction | Contrast it serves |
|---|---|---|
| **A0** | No memory | Control |
| **R25** | Random 25% of the corpus: 168 trajectories, sampled with seed 2027, stratified to keep the PASS/FAIL ratio. Same map notes (reused, because map is per-trajectory), same group, reduce and index code as M3 | Evidence breadth (H1) |
| **M3** | Whole corpus: v5 topics plus a deterministic complete index (`memory/frozen-v5-fullindex`, digest `4a2eb528…`) | Reference memory |
| **G** | M3 passed through the automated governor (§2) | Governance (H2) |
| **GR** | M3 with the *same number* of units removed as G, chosen uniformly at random (seed 2027) from the same eligible units, with the same reassembly | Size-matched control for G (H3) |

**M2** (v5 as generated, with the truncated index) is not a confirmatory arm. M2 versus M3 is reported only as an exploratory discoverability check.

Every arm uses the same reassembly and index code. Every arm must pass the official `check_memory` and is frozen read-only with its digest before trials.

## 2. The governor (arm G): a software pipeline

The governor is part of memory generation, so it follows the same rules: it sees only the corpus, uses no web, and never sees a task map. It takes M3 and the corpus as inputs and outputs a memory folder.

1. **Segmentation** (deterministic parser, no model). Each topic file is split into *units*: a heading, bullet, numbered item, paragraph, or fenced code block. Headings are structural and are never removed. The parsed citations (`inputs/tNNNN.json#step=K`) are attached to each unit.
2. **Rule R-artifact** (deterministic). A fenced code block of more than 12 non-blank lines is removed. This operationalizes the official instruction's ban on reproducing prior final artifacts. The threshold is fixed here.
3. **Evidence retrieval** (deterministic).
   - A unit with resolvable citations gets its cited steps as evidence.
   - Otherwise it gets the top-3 steps by BM25 over the trajectories in the unit's topic group (from `groups.json`).
   - Each step is truncated to 2,000 chars, and each step's trajectory outcome (PASS or FAIL) is included.
4. **Evidence judge** (model). The prompt is fixed and committed before running. It receives the unit, the evidence and the outcomes, and outputs JSON with a `verdict`: `supported`, `contradicted`, or `insufficient`.
   - **Judge model:** an open model from a *non-Qwen* family of 20–35B parameters, run locally through Ollama at temperature 0. The exact tag and digest are recorded at freeze.
   - **Fallback:** if none can be obtained by Nov 3, the fallback is `qwen3-coder:30b`. The model-family correlation is then declared.
5. **Admission rule (primary).** A unit is dropped if its verdict is `contradicted`, or if R-artifact removed it. Everything else is kept.
   - **Separation rule, decided before seeing any trial:** if the primary rule removes fewer than 5% of non-heading units, the strict rule is applied instead. The strict rule also drops `insufficient` units that contain a concrete technical assertion (a number, an identifier in backticks, or a command).
   - The governor's unit counts are reported either way. This prevents the earlier failure mode, where the governed and ungoverned arms were nearly identical.
6. **Reassembly** (deterministic). Each topic file is rebuilt from its kept units in their original order. A file left with only headings is dropped. The complete index is regenerated with the same code as M3.

**Judge validation** (automatic, before freeze, with no human labels and no task data):
- Synthetic contradictions are made from 100 units sampled from M3. Each is perturbed by a fixed perturbation script: a changed number or flag, a swapped identifier, or a negated directive. These are judged against the original evidence.
- Sensitivity is the share of perturbed units judged `contradicted`. Specificity is the share of the 100 unperturbed units judged `supported` or `insufficient`.
- **Gate:** sensitivity ≥ 0.6 and specificity ≥ 0.8. If the gate fails, the prompt may be revised **once**, and only on this synthetic set. Both attempts are reported.

## 3. Tasks and trials

- **Tasks:** the locally runnable official v1.0 tasks whose grading path passes an oracle check by **Nov 5**. Candidates are build-word2vec-pipeline, dapt-intrusion-detection-workflow-learning, cattrs-compositional-changelog, cookie-store-compositional-changelog, awilix-release-tier-implicit, awilix-release-tier-explicit, and customer-delivery-contextual-preferences. A task that is not validated by Nov 5 is excluded, and the reason is reported.
- **Task agent:** Codex CLI 0.157.0-alpha.11.1, with the official `$CODEX_HOME/memories` mechanism, `features.memories=true` in every arm, and web search off. The model is local `qwen3.8:27b-mtp-q4_K_M` with 65,536 context and effort `medium`.
- **Trials:** k = 3 per arm per task, fresh workspace each time. There is one job per task. Within a job, arm order follows a fixed balanced sequence of 15 trials (3 rounds of a Latin rotation of A0, R25, M3, G, GR) and is committed.
- **Validity:** infrastructure failures (a Harbor exception, no grading, or an infra timeout) are rerun at the end of the same job and not scored. Agent-caused failures score 0 (D5'). No other exclusions.

## 4. Outcomes and analysis

- **Primary outcome:** strict pass (verifier reward = 1) per trial.
- **Secondary outcomes:** fraction of cases passed; agent wall time; output tokens; whether the agent read the memory folder (from the trace).
- **Primary contrasts** (Holm-corrected across the three):
  - **H1 (breadth):** M3 > R25.
  - **H2 (governance):** G is not worse than M3. Non-inferiority margin: −1 strict pass in total across all tasks. Superiority is reported if present.
  - **H3 (governance versus removal):** G > GR.
  - **H0** (M3 > A0) is reported as the benchmark-validity check.
- **Tests:** exact paired sign-flip permutation over tasks, applied to the per-task difference in strict pass rate, with a secondary run on the case fraction. Pooled counts and per-task tables are shown for every arm.
- **Power caveat, stated in advance:** with about 5–7 tasks × 3 trials, only large effects are detectable. The paper reports effect sizes with exact intervals and does not claim equivalence from a null.

## 5. Memory-quality audit (measurement, not construction)

Run automatically on every arm's frozen memory:
- unit counts;
- code-block units longer than 12 lines;
- the judge's verdict distribution;
- the share of units with resolvable citations.

This audit does not feed back into any arm.

## 6. Declared deviations from the official protocol

- **Task model:** local Qwen, not GPT-6 Sol or Opus 5.5.
- **Task subset:** local tasks only.
- **Memory generation time:** the map and reduce wall time on local GPUs is about 7 h, against the official 6 h limit.
- **Network modes:** staged as `public`, because Harbor's Singularity backend rejects `no-network`.
- **Prompt header:** the runner's "Required output artifacts" header is added.
- **Memory map notes:** reused across R25, M3, G and GR, which is equivalent to rerunning the per-trajectory map.

## Amendments

### A1 (2026-10-29): governor judge. Made before any trial of G or GR, using only synthetic validation data

**Why.** The first validation (job 303211, gemma3:27b, judge prompt sha `59e83a40…`) gave sensitivity 0.12 and specificity 0.92, so the gate failed.
- In 59 of the 100 perturbed units, the changed token does not appear in the unit's evidence. No judge could detect those perturbations, so the validation design itself was flawed.
- Judging all 11,299 units would take about 19 h.

**Changes:**
1. **Validation set.** 100 units sampled with seed 2027 from M3 units that carry resolvable citations *and* whose perturbed token occurs in the unit's evidence. These are detectable perturbations. The specificity set is the same 100 units, unperturbed. The gate is unchanged: sensitivity ≥ 0.6, specificity ≥ 0.8.
2. **The one allowed prompt revision.** The judge must first quote the evidence span about the same entity, then compare specific values, identifiers and directives. It answers `contradicted` when the evidence states a different value, identifier or directive for the same thing.
3. **Judge model chosen by validation.** Both `gemma3:27b` (non-Qwen) and `qwen3.8:27b-mtp-q4_K_M` are validated with the revised prompt.
   - Use the one that passes the gate with the higher sensitivity; on a tie, the non-Qwen model. Same-family correlation is declared if Qwen is chosen.
   - If neither passes, arms G and GR are dropped from the confirmatory matrix. The judge failure is then reported as a finding.
4. **Judging scope.** Only *technical* units are judged: those containing a digit, a backticked span or a command-like token, using the rules.py predicate. Non-technical units are always kept.
   - Primary rule: drop technical units judged `contradicted`, plus the R-artifact units.
   - Separation rule (if under 5% of non-heading units are removed): also drop technical units judged `insufficient`.
   - GR samples from the same non-heading population as before.
5. Governor outputs are written under the git-ignored `results/governor-run-*/`.

### A2 (2026-10-29): deterministic grounding governor. Made after the A1 judge failure, before any G or GR trial; no task outcomes seen

**Why.** Under A1, neither local judge passed the gate on detectable perturbations:

| Model | Job | Sensitivity | Specificity |
|---|---|---|---|
| gemma3:27b | 303219 | 0.16 | 0.85 |
| qwen3.8:27b | 303220 | 0.21 | 0.98 |

Per A1, the LLM-judge governor is **dropped**, and its failure is reported as a finding: local 27B judges cannot verify the claims in memory lessons against trajectory evidence.

A1 prescribed dropping G and GR. **This amendment replaces that outcome with a different, model-free governor.** It is declared as a second design choice made after a construction-time failure. Results for G under A2 are reported together with this history.

**G (A2) rule.** The pipeline is unchanged except for steps 4–5.
1. **Concrete tokens.** For each *technical* unit (rules.py predicate), extract:
   - backticked spans, compared case-sensitively;
   - standalone numbers, excluding citation markup and step indices.
2. **Grounded.** A unit is grounded if every extracted token occurs in its evidence. The evidence is the cited steps when citations resolve, otherwise the top-3 BM25 steps within the topic group, as in §2. Backticked spans are matched as substrings; numbers are matched as numeric tokens.
3. **Admission.** Drop ungrounded technical units and R-artifact units. Keep non-technical units. No separation rule applies.

**Validation, same sets as A1:**
- Sensitivity is the share of perturbed units dropped.
- Specificity is the share of original units kept.
- The gate is unchanged: sensitivity ≥ 0.6 and specificity ≥ 0.8.
- There are no revisions. If the gate fails, G and GR are dropped for good.

**GR:** the same number of units removed uniformly at random (seed 2027) from all non-heading units, as before.

### A3 (2026-10-29): governance arms dropped; matrix and audit updated. Before any confirmatory trial; no task outcomes seen

**Governor result.** The A2 grounding rule failed its gate on the A1 validation set: sensitivity 0.62, specificity 0.50. Per A2, **arms G and GR are dropped for good. There will be no further governor amendments.**

**Confirmatory arms:** A0, R25, M3.
- **Trial count:** with the trial budget unchanged, **k = 5 per arm per task**.
- **Order:** within each task job, 5 rounds of a Latin rotation over (A0, R25, M3).
- **Primary contrasts:**
  - H0: M3 > A0.
  - H1: M3 > R25.
  - Both are Holm-corrected, using the analysis in §4.

**The memory-quality audit (§5) is extended.** It is measurement only and does not feed back into any arm. It runs on M2, M3 and R25:
- the A2 grounding rate for all technical units, split into units with cited evidence and units with BM25 evidence;
- R-artifact counts;
- the share of units with resolvable citations.

The validation results for the A1 judges and the A2 rule are reported as findings about verifying lessons automatically.

**Scope-leakage analysis.** This is the timeline item #21, now made concrete:
- For each task and memory arm, compare against A0.
- Tag a trial as "memory consulted" when the trace shows the agent opening memory files, and record which topic files it opened.
- Classify each opened file as same-family or other-family. The classification uses only the topic file name and the task's *name*: a deterministic token overlap of at least 1 shared content word. It never uses task content.
- Report how often harmful trials involve other-family topics. This is descriptive only.

## Freeze (2026-10-29)

These are frozen before any confirmatory trial.

| Item | Value |
|---|---|
| Arms | A0 (no memory); R25 `memory/frozen-r25`, digest `75be173fb8b1332429bac0fc23323e9e62cd9fbf36c3e9740840d217461cf4c6`; M3 `memory/frozen-v5-fullindex`, digest `4a2eb5286366d650260af0b873a91be9f99b2891a327f0ae73ba8c2e8ef0517a` |
| Tasks (all 7 validated against the oracle) | build-word2vec-pipeline, dapt-intrusion-detection-workflow-learning, cattrs-compositional-changelog, cookie-store-compositional-changelog, awilix-release-tier-implicit, awilix-release-tier-explicit, customer-delivery-contextual-preferences |
| Trial order per task job | `A0 R25 M3 R25 M3 A0 M3 A0 R25 A0 R25 M3 R25 M3 A0` (5 rounds, each arm 5 times) |
| Runner | commit of tag `prereg-v1`; per-job snapshot |
| Calendar | No fixed dates (user, 2026-10-29). Each task's job starts once its GPU smoke trial has run cleanly. Smoke and earlier exploratory trials are not pooled |

Infrastructure reruns follow §3. If a task job is lost to infrastructure, the whole task job is rerun with the same order, and the loss is reported.

## Amendment A4 (2026-10-29): memory exposure. Analysis only; added before any confirmatory memory trial

**What we found.** These findings come from the exploratory trials (jobs 303129, 303133, 303198; 9 memory trials).
- Codex 0.157 puts the memory summary (our `MEMORY.md`) into the prompt but keeps only its **first 5,000 and last 5,000 characters**. Everything in between is replaced by "…N tokens truncated…".
- In those trials the agent never opened `MEMORY.md` or any topic file. So all the memory the model actually used was this window.
- `scripts/memory_exposure.py` reproduces the window exactly ("match" on all three jobs).

What each arm shows the model, by count of topic entries:

| Arm | `MEMORY.md` size (chars) | Topic entries in `MEMORY.md` | Entries in the visible window |
|---|---|---|---|
| v5 (exploratory only) | 16,369 | 106 | 61 |
| R25 | 26,893 | 116 | 65 (offline estimate; checked on its first trial) |
| M3 | 46,625 | 324 | 83 |

- M3's appended complete index falls mostly inside the truncated middle.
- M3 *hides* all Word2Vec topics that v5 showed.
- No arm makes a DAPT-specific topic visible.

**Nothing below changes the arms, memories, order, tasks, k or primary analysis.**

1. **Exposure covariate.** For every memory trial, record:
   - the visible window, from the logged request bodies, checked against the offline reproduction;
   - the topic files the agent opened, if any.
2. **One directional prediction, stated now.**
   - On build-word2vec-pipeline, M3's strict pass rate will not exceed A0's by more than 1 of 5 trials. The reason is that M3 shows no Word2Vec topic, whereas v5 did (and v5 went 0/3 → 3/3).
   - This is descriptive and is not added to the Holm family.
3. **Scope leakage.**
   - The §4 rule is applied to the topic entries in the visible window as well as to opened files.
   - "Content word" is frozen as: lowercase tokens split on non-alphanumerics, length > 2, excluding the stop list in `scripts/memory_exposure.py`.
   - Generic words ("pipeline", "learning", "workflow") are *not* stop words under the frozen rule, so same-family counts are upper bounds. This is reported as a limitation.
4. **Interpretation.** M3 was meant to add a complete index. Under this mechanism the index is mostly invisible. M3 is kept as frozen and reported as "a longer summary whose window differs from v5". It is not reported as "a full index".

## Amendment A5 (2026-10-29): conservative case count for patch tasks. Analysis only, added before any confirmatory result

- In patch tasks, the official verifier also collects any tests the agent adds. Example: smoke job 303274 collected 202 tests, against 184 in the oracle check.
- The recorded secondary metric `cases_passed = min(passed, cases_total)` can therefore hide failures among the original cases.
- Alongside it, we also report a lower bound computed from recorded counts: `cases_passed_lb = max(0, passed − max(0, collected − cases_total))`.
- Conclusions from the secondary metric require both values to agree in direction.
- The primary metric (strict reward from the official verifier) is unchanged.

## Amendment A6 (2026-10-31): Word2Vec mechanism ablation. Exploratory, added before any of its trials

**Why.** On build-word2vec-pipeline, both memory arms pass 5/5 against A0 0/5 (job 303281), and every memory trial searched the memory folder. Two questions are open: did the help come through the injected window or through agent search, and is it the Word2Vec-specific content or memory in general? This amendment adds a separate exploratory job. It changes nothing in the confirmatory matrix, its Holm family or its analysis.

**Arms.** All three are built from frozen M3 (`4a2eb528…`) by a deterministic script. Each derived memory is frozen by digest before its first trial.
- **M3** (control, rerun in the same job).
- **M3-S (search only).** The memory folder adds a fixed one-line `memory_summary.md`: "Index of past-run notes: MEMORY.md in this folder; topic files are in topics/." Codex injects this file instead of `MEMORY.md`, so the injected window contains no topic content. `MEMORY.md` and all topic files are unchanged and remain searchable.
- **M3-W (minus Word2Vec).** Remove every topic file whose name or content contains "word2vec" (case-insensitive), and every `MEMORY.md` line that contains it. Everything else is unchanged.

**Design.** One job on build-word2vec-pipeline, k=5 per arm, order `M3 S W S W M3 W M3 S M3 S W S W M3` (the frozen Latin pattern with A0→M3, R25→M3-S, M3→M3-W). Same runner, model, prompt, timeout and grader as the confirmatory matrix. It runs only after the confirmatory matrix has finished. The runner changes needed for the new arms are made only then, because queued confirmatory jobs read the live runner.

**Predictions, stated now. Descriptive; no tests.**
1. M3-S ≥ 4/5 strict: search alone carries the effect.
2. M3-W ≤ 1/5 strict: the effect depends on Word2Vec-specific content.

If prediction 2 fails, the effect comes from memory that does not name Word2Vec, for example a general output-format convention. That outcome is reported as is.

**Limitation.** The M3-W rule removes only content that literally names Word2Vec. Related content under other names stays.
