# Failure taxonomy for the FrontierMemory trials

Status: v1, written before any trial was classified. Buckets and decision rules below are fixed first so the per-arm analyses cannot fit them to what they find. Changes after this point go in the amendments list at the end.

Scope: the 385 failed trials (strict reward below 1) in the 10 counted sets: control, runs 1, 3, 4, placebo, read-first, all-shown, none-shown, evidence, blend. 45 trials per set, 450 in all, 65 passes. The second machine's Codex pair is a separate study and is out of scope.

## 1. Principle

A trial fails when the final state of the task environment does not satisfy the verifier. Memory can change that outcome only by changing what the agent does. So every failure asks four questions in order, and the order is the design:

1. **Was there a failure the agent could not have avoided with any memory?** (grader, environment, capability, infrastructure.) If yes, memory is not the cause, whatever the arm.
2. **If memory could have helped, did the right information exist in the memory the arm used?**
3. **If it existed, did it reach the agent's context, or was it reachable?**
4. **If it reached the agent, did the agent use it correctly?**

A bucket is the first question answered "no" (or "cannot tell"). Because the chain is serial, every failure has exactly one **primary bucket** (the earliest broken link) and any number of **secondary tags** (other links that were also broken). That makes the buckets mutually exclusive and countable, and the tags keep the information that "also unavailable" would otherwise hide.

Two traps this design avoids:
- **Attributing a no-memory-reachable failure to memory.** Six of the 15 tasks have 0 passes in all 10 arms (30 trials each; the first draft said seven, see amendment 1). For most of those, nothing in the memory pathway can be blamed until the task-side buckets (section 3, group A) are ruled out.
- **Counting "memory not opened" as a memory failure when the memory held nothing relevant.** "Not opened" is only a failure of delivery if the memory contained something that would have changed the outcome.

## 2. The pipeline and what each stage can do to a trial

Every arm is a plug-in to the same outer pipeline (`results/arm-designs.md`):

| Stage | What happens | Where it lives |
|---|---|---|
| P0 Source | Past agent runs (corpus v1.1, 750 runs, gated) exist or do not for the task | `data/corpus`, `results/corpus-coverage.json` |
| P1 Generation | Hermes `/learn` (or an arm's own builder) turns the corpus into a memory folder; 6-hour limit; exports only at the end | `official/vm/`, generation logs |
| P2 Memory artifact | Skills (SKILL.md plus references), MEMORY.md index, byte size, descriptions | frozen memory dirs, `memory_sha256` |
| P3 Staging | Folder copied into the task container at a path the agent can see | arm adapter, `fm_local/*_hermes.py` |
| P4 Exposure | What is in the model's first request: MEMORY.md block, `<available_skills>` index, everything (all-shown), nothing (none-shown), a nudge (read-first), a task rewrite (blend), a pointer (evidence) | saved system prompt, `arm_check.py` |
| P5 Access | The agent opens a skill or file; which one; when | `memory-access-*.jsonl`, trajectory |
| P6 Application | The agent acts on what it read; context grows over a long run | trajectory |
| P7 Execution | Plain task work: planning, coding, tool use, finishing in time | trajectory, agent logs |
| P8 Environment and serving | Image build, network proxy, model server, relay, timeouts | `serving-incidents*.json`, ollama logs, relay logs |
| P9 Submission | Output exists in the form the verifier reads (file path, commit, final answer) | trial workspace |
| P10 Verification | Hidden tests or LLM judge produce a reward | verifier logs, `judge_status` |
| P11 Scoring | Strict reward: 1 only if every check passes; partial credit is separate | `partial-credit-*.jsonl` |

## 3. Failure buckets

IDs are stable. "Detect" says what evidence settles the bucket; "needs" says which data layer it depends on (section 6).

### Group A. Not attributable to memory (the trial could not pass, or would fail the same way with any memory)

| ID | Bucket | Definition | Detect | Needs |
|---|---|---|---|---|
| A1 | Grader-infeasible | The task's own reference solution scores below 1 under this verifier (reference scores 0 on 4 of 15 tasks and 0.83 on one: `results/pipeline-audit.md`), so a strict pass is not defined for most attempts | oracle result for the task, `docs/maintainers.md` | host |
| A2 | Grader-undetermined | LLM judge returned a score but no check was made that it separates correct from incorrect outputs (APEX tasks use Claude Opus 5.5 where GPT-5.6 Sol is documented); a failed judge also scores 0 | `judge_status`, judge scores, `parts` | host, partly VM |
| A3 | Task beyond the model | The agent made a real attempt with a valid environment and the output is wrong or incomplete for reasons of capability (wrong algorithm, misread spec, partial work), and nothing in the corpus or memory concerns what was missed | trajectory plus verifier output; partial credit shape | VM |
| A4 | Environment or build failure | Image build failed, dependency drifted (floating installs, anyio pin, Word2Vec's floating branch), network egress blocked, tool missing | build log, trial exception | VM |
| A5 | Serving or infrastructure fault | Model server stall, relay timeout, proxy cut, Hermes gave up on the server (`model_unavailable`), container teardown | `serving-incidents*.json`, `model_unavailable`, ollama logs | host |
| A6 | Time or budget exhaustion | Agent hit its time limit, step limit, or token budget before submitting | agent start and finish times, tokens, `AgentTimeout` | host (times, tokens), VM (reason) |
| A7 | Output not produced or in the wrong place | The workspace has no file at the path the verifier reads, or the commit is missing (the official prompt names no path for Word2Vec) | workspace listing | VM |
| A8 | Cheating or constraint violation avoided or detected | Trial passes or fails because of a shortcut the rules forbid (tests edited, reference read) | trajectory | VM |

A1 and A2 are task properties, so they are assigned per task, not per trial, before any trial-level reading. A trial gets A1 or A2 as primary only if the agent's output was otherwise on track; if it failed for a reason that would also fail a correct solver, A3 to A7 may apply as well and are recorded as secondary tags.

### Group B. Memory could have helped; the chain broke before the agent

| ID | Bucket | Definition | Detect | Needs |
|---|---|---|---|---|
| B1 | No source | The corpus has no related run for the task (8 of 15 tasks at 50% overlap in both corpus versions), so no generator or evidence arm could have supplied task-specific content | `corpus-coverage.json` | host |
| B2 | Memory does not exist | No memory was produced (run 2 and the generator arm hit the 6-hour limit and exported nothing; those arms have no trials) or the arm gave this task nothing (evidence with 0 related runs, blend task excluded) | arm report, file count | host |
| B3 | Generation lost it | Source runs for the task exist, but the memory has nothing about the needed point. Sub-tags: B3a never read (tool output was 0.2% of the corpus in a compliant pass), B3b read and dropped in summarisation, B3c merged into a vague skill, B3d wrong lesson (stated incorrectly) | memory text against source runs and the task's verifier | VM for memory text; host for `frozen-v*` |
| B4 | Memory present but not specific | The right lesson is there, but under a generic name and description so an index cannot point to it (the benchmark blog's "never loaded" case) | skill name and description against the task | VM |
| B5 | Staging fault | Memory was meant to reach the container but did not (wrong path, copy failed, folder empty, arm adapter bug) | arm check, container listing | VM |
| B6 | Exposure fault | The memory reached the container but not the model: harness truncation or cap, MEMORY.md block missing, index absent or names-only (Hermes collapses some categories), nudge missing from the saved system prompt (read-first's first end-to-end failure), all-shown block cut | saved system prompt per trial, `arm_check.py`, `exposure_measure.py` | VM |
| B7 | Exposure by design is nil | The arm deliberately shows nothing (none-shown), or one skill out of many (scoped, not run), and the agent never found the file | arm definition, access log | host (definition), VM (log) |
| B8 | Context pressure | Memory shown but crowded out: all-shown fills the prompt, the agent's context grows and the memory falls out of attention (long runs), or the model's context window (262,144 tokens requested) is exceeded | prompt tokens per request, final context size | VM |

### Group C. Memory reached the agent; the agent did not use it well

| ID | Bucket | Definition | Detect | Needs |
|---|---|---|---|---|
| C1 | Not accessed, relevant memory shown | Memory contained a point that would have changed the outcome, the agent saw the index or the block, and never opened the skill | access log with a relevance judgement against the verifier | host (opens only for run 1 and read-first), VM for the rest |
| C2 | Opened the wrong skill | The agent opened something, not the relevant item | access log, skill relevance | host/VM |
| C3 | Opened too late | Relevant skill read after the decisive work was done (first open turn versus the turn where the error was committed) | `first_open_turn`, trajectory | host (run 1, read-first) / VM |
| C4 | Read but not applied | The agent read the relevant instruction and did something else, forgot it, or applied it to the wrong object | trajectory | VM |
| C5 | Applied but misapplied | Followed the memory and it made things worse: stale or wrong content, over-literal reading of a preference, a placebo-style distraction | trajectory against ground truth | VM |
| C6 | Applied correctly; still failed | Memory-guided behaviour was right, but a downstream gap (A3 to A7) remained; the memory was not sufficient | trajectory | VM |
| C7 | Memory-induced cost | Reading memory used turns or time that pushed the trial into A6 (time limit), or the longer prompt changed the behaviour (length confound) | token and time deltas against control, placebo | host (times, tokens) |

### Group D. Cannot be assigned

| ID | Bucket | Definition |
|---|---|---|
| D1 | Undeterminable from retained evidence | The logs needed to separate buckets were not kept or are not reachable. This is a first-class result: it is counted and reported, never folded into another bucket. |
| D2 | Mixed or ambiguous | Two or more buckets are equally supported and the rule in section 4 does not break the tie. |

## 4. Assignment rules (apply in this order)

1. **Task level first.** Fix A1 and A2 per task from the oracle and judge evidence, then B1 (source coverage). These are not trial-specific and are written down before any trajectory is read.
2. **Trial level, in pipeline order.** For each failed trial, test buckets in the order A5 → A4 → A6 → A7 → B2 → B5 → B6 → B7 → B8 → B1/B3/B4 → C1 → C2 → C3 → C4 → C5 → C6 → A3, stopping at the first one the evidence supports. A3 is last on purpose: "the model was not good enough" is the explanation that fits every failure and so needs the other explanations ruled out first.
3. **Need before blame.** For B3 to C7, first state in one sentence what the memory would have had to say to change the outcome, and say where in the verifier's checks that matters. If no such sentence exists, the bucket is A (nothing memory could have supplied), not B or C.
4. **Counterfactual evidence grade** on every assignment, recorded in a field:
   - **O** observed: a log, file or trajectory line shows it.
   - **P** paired: shown by comparing this trial with the control or sibling attempts of the same task (for example, the same wrong answer in control and memory arms).
   - **I** inferred: reasoned from task, memory and arm design without a trial-level record.
   - **U** unknown: cannot be determined; use D1.
5. **Siblings count.** Each task has 3 attempts per arm. Where attempts differ (one passes, two fail), a failure that is not repeated in the passing attempt is a stronger candidate for C or A6 or A5 than for A1 to A3.
6. **No mixed-grade totals.** Bucket counts are reported per evidence grade, so that a table dominated by I cannot be read as if it were O.

## 5. Which buckets each arm can have

"Yes" means the stage exists for the arm. "No" means the bucket is structurally impossible and a trial assigned there signals a classification error.

| Arm | What the agent gets | Memory-chain buckets that apply | Special risks |
|---|---|---|---|
| Control | No memory | A1 to A8 only; B and C do not apply. Also record **headroom**: what memory could have supplied (needed for the "need before blame" rule) | Baseline failure reasons set the floor for every other arm |
| Runs 1, 3, 4 (Hermes /learn memory) | MEMORY.md block + `<available_skills>` index; bodies on demand | All of B1 to B8, C1 to C7 | Run 1 had memory opened in 15 of 45 trials; run 4 replaced run 2 after a timeout; each run has different content |
| Placebo | Memory-shaped Moby-Dick text, same count and byte lengths | A group; B6 (exposure of placebo); C5 (distraction, length), C7. B1 to B4 do not apply (no content to be missing) | A "failure" here is a failure with noise in the prompt; compare with control sibling attempts |
| Read-first | HM plus one sentence telling the agent to check memory first | All B and C; B6 includes "sentence in system prompt"; C3 is mostly resolved by design but C4 and C5 remain | First end-to-end check failed because the sentence was missing from the saved prompt |
| All-shown | Every memory file in the system prompt | B8 (context pressure), C4, C5; B7 does not apply | 10 trials stalled and were rerun; the raw 5/45 is replaced by the rerun set |
| None-shown | Files on disk, nothing advertised | B7 central; C1 to C3 if the agent found files anyway | The agent can only use memory by exploring |
| Evidence | The task's related raw runs in `/tmp/hermes/records`, plus a pointer line | B1, B2 (0 related runs for 8 of 15 tasks), B5 (records staged), C1 to C5 on raw logs; B3 to B4 do not apply (no generation) | Word2Vec 3/3; customer delivery gets nothing, equal to control |
| Blend | Run 1's memory rewritten into each task description | B3 inherits from run 1; plus **rewrite fidelity**: rewrite dropped, distorted or over-emphasised a lesson; one task excluded; B6 does not apply (always shown); C1 to C3 do not apply | Missed its written bar (3/45 strict) |

## 6. What data exists, and what that limits

- **On this host:** per-trial `summary-*.jsonl` (reward, tokens, start and finish times, exception, judge status, memory digest); `partial-credit-*.jsonl` (strict versus partial per trial, with `parts` for some); `audit-*.txt`; `memory-access-run1.jsonl` and `memory-access-readfirst.jsonl` (opens, first open turn, paths); `serving-incidents*.json`; corpus coverage; task sources and the oracle results; the frozen memories from the earlier study (v1 to v5), the decision log with trial-level notes.
- **Not on this host:** the trial directories (agent trajectories, saved system prompts per request, workspace snapshots, verifier logs, container logs) and the generated memories of runs 1, 3, 4 and the evidence and blend inputs. They live in the VM disk image on the compute node. That node (`nodevcggpu02`) has been down since 2026-11-14 21:00 (Slurm: not responding), and the cluster job has been released.

So the buckets marked **VM** above cannot be settled from this host today. The analysis proceeds in two layers:
- **Layer 1 (now):** task-level buckets (A1, A2, B1, B2 and arm structure), the sibling and paired comparisons, timing and token features (A5, A6, C7), and the run 1 and read-first access logs (C1, C3). Everything else is reported as D1 with the reason.
- **Layer 2 (once the disk is reachable):** trajectory-level assignment for every trial, using a single read-only extraction script written in Layer 1.

## 7. Research basis for the stage list

Each stage is included because a published failure mode or a repo-verified fact exists for it. The repo's own sources (opened for `results/arm-designs.md`) are reused; none are added from memory here.

- **P1/P2 generation and artifact:** brevity bias and merged or dropped items (Agent Context Engineering, arXiv 2510.04618); descriptions that state what the skill does and when to use it (Anthropic skill authoring guidance); focused skills over exhaustive bundles (SkillsBench, arXiv 2602.12670); the benchmark blog's skill that was "never loaded" because of a generic description.
- **P4 exposure:** harness caps and truncation rules (`results/harness-exposure-survey.md`: Codex 2,500 tokens head and tail, Claude Code first 200 lines or 25 KB, Hermes loads in full); progressive disclosure shows only names and descriptions at start (Agent Skills best practices); the Hermes names-only category collapse.
- **P5 access:** agents under progressive disclosure often do not open skills (memory opened in 15 of 45 trials in run 1; 5 of 7 passes came without opening); retrieval accuracy depends on the description or the body (SkillRouter, arXiv 2603.22455; Liu et al., arXiv 2604.04323).
- **P6 application and context:** length alone hurts even with perfect retrieval (Du et al., arXiv 2510.05381); position effects (Lost in the Middle, TACL 2024); always-on context files raise cost without raising success (Gloaguen et al., arXiv 2602.11988); skill gains shrink under realistic retrieval.
- **P7 to P11 task side and grader:** reference solutions failing the strict verifier, floating installs, the judge substitution and no agreement test (`results/pipeline-audit.md`, `docs/maintainers.md`).
- **Harness effects:** the same model scores differently across harnesses (Terminal-Bench, arXiv 2601.11868; HAL, arXiv 2510.11977), which is why exposure (P4) is a stage and not a footnote.

## 8. Output format each arm analysis must produce

One file per arm, `results/failure-analysis/arm-<name>.md`, and one machine-readable `results/failure-analysis/arm-<name>.jsonl` with one line per failed trial:

```
{"arm", "trial", "task", "attempt", "reward", "partial", "primary_bucket", "secondary_tags": [],
 "evidence_grade": "O|P|I|U", "evidence": ["file:line or field", ...],
 "need_sentence": "what memory would have had to say, or null",
 "sibling_note": "what the other two attempts did"}
```

Rules for the analysts:
- Cite the exact field, file or line behind every assignment. A bucket with no cited evidence is D1.
- Do not read the paper, the deck or the summary documents for conclusions. Read them only for definitions.
- Report the count of D1 per task and why.
- Do not use the result of other arms to assign a bucket in this arm except through rule 5 (siblings) and the paired comparison against control.
- Do not edit any repo file other than the two outputs for your arm.

## Amendments

1. Correction (from TASK-LEVEL.md, computed from the summary files): six tasks, not seven, have 0 of 30 passes (eurogrid, chatgpt-proposal, both awilix, customer-delivery, DAPT). The next lowest are partnership contract 1/30, cookie store 2/30, Teams 2/30. No bucket definition changed.
2. Per-task facts (A1, A2, B1, headroom, partial-credit profile, time use) are fixed in `TASK-LEVEL.md` and are shared input; arm analysts must not re-derive or contradict them without reporting the conflict.
3. Correction (from arm-evidence.md section 7, text scan of the staged records): the evidence arm staged files for 11 of 15 tasks, not 7. Only 4 tasks (both awilix, cattrs, customer-delivery) got nothing. The staging rule also admits runs whose opening names the task's repo or family, so many staged files are other tasks' runs. Section 5's "0 related runs for 8 of 15 tasks" describes the corpus coverage relation at 50% overlap, not what was staged. TASK-LEVEL.md's B1 run counts (coverage relation) differ from the staged counts for APEX market-share, seat-surplus, Eurogrid, cookie store and Word2Vec; the verdicts agree in substance. Bucket definitions are unchanged.
