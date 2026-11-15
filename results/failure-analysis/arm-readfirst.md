# Failure analysis: READ-FIRST arm (fm-tasks-arm-readfirst)

45 trials, 8 strict passes, 37 failures. Memory is run 1's (sha256 c3d6f31a4...) with standard delivery plus the one-sentence nudge. Machine-readable twin: `arm-readfirst.jsonl` (37 lines). Buckets and grades follow `TAXONOMY.md`; per-task facts follow `TASK-LEVEL.md`. Trial directories, trajectories, saved prompts, verifier logs and the text of run 1's memory are not on this host, so most failures are D1.

## 1. Method

- Layer 1 only. Inputs: `official/summary-fm-tasks-arm-readfirst.jsonl`, `partial-credit-fm-tasks-arm-readfirst.jsonl` (strict, partial, parts), `audit-fm-tasks-arm-readfirst.txt`, `memory-access-readfirst.jsonl` and `memory-access-run1.jsonl`, control and run 1 summary and partial files, `official/vm/serving-incidents*.json`, `decisions-log-detailed.md` (D125 to D132, D134), `official/fm_local/arm_check.py`, `scripts/memory_access.py`.
- Rule order of section 4 applied per trial. A5, A6: no exception, no timeout, no model_unavailable in any of the 37 (summary), and neither incident file lists a read-first window (O). B6 (nudge missing): the first end-to-end check did fail for this reason (D125, A7), the fix rebuilt the API-time prompt (D126, D128), and the counted set's arm check passed on all 45 trials (D132; audit `ISSUES: none`). That is an O-grade log statement, but the per-trial `arm_check` output itself is not on this host, so B6 is excluded on the decision log, not on a file I read.
- `attempt` is the order of the trial within its task in the summary file. Trial names are random, so attempt order has no meaning beyond labelling.
- Access fields: `first_open_turn` is the assistant-turn index of the first memory open (0 = first message). `tool_calls_before_first_open` counts tool calls, and can exceed the turn index because a turn may hold several calls. "Open" includes reference files read alone and one directory-level open of `skills` (trial xhCnCoA, partnership).
- D1 is used whenever the bucket depends on a trajectory, verifier log or memory text. Candidate tags (`C1_candidate`, `C4_C5_C6_candidate`, `late_open_C3_candidate`) record what the access log permits, not an assignment.

## 2. The memory, as far as the logs show

D134 (decision log): every Hermes /learn memory we have, run 1 included, is exactly one skill plus 5 to 12 supporting files; the SKILL.md of run 1 is 6,540 bytes. The access logs show its identity: one skill, `agent-evals/eval-task-families`, with references `family-analysis-mcp`, `family-office-mcp`, `family-workflow-automation`, `family-swe-repo`, `family-pcap`, `failure-modes`, `commands`, `paths`, and `contracts` (opened once, in run 1). So "which skill was opened" has one answer in every trial; the informative field is which reference file the agent followed. What is inside each file is unknown here.

Fit of reference names to task headroom (grade I, from names only):

| Reference | Fits tasks | Opened in read-first for |
|---|---|---|
| family-analysis-mcp | three APEX tasks | market share 3/3, seat surplus 1/3, eurogrid 3/3 |
| family-workflow-automation | three AutomationBench tasks | chatgpt proposal 1/3, partnership 3/3, marketing 1/3 |
| family-office-mcp | EnterpriseOps CSM, marketing | csm 1/3, marketing 1/3 |
| family-swe-repo | awilix x2, cattrs, cookie store, customer delivery, word2vec | awilix 4/6, cookie 2/3, word2vec 3/3 (cattrs and customer: SKILL.md only) |
| family-pcap | DAPT | 3/3 |
| (none obvious) | EnterpriseOps Teams | never opened (0/3, also 0/3 in run 1) |

Name-fit does not mean the content has the needed point. For tasks with no related source run (TASK-LEVEL B1 YES: awilix x2, cattrs, customer delivery, eurogrid) the family file can hold at most generic advice.

## 3. Bucket counts per evidence grade

| Bucket | O | P | I | U | Trials |
|---|---|---|---|---|---|
| A1 | 3 | 0 | 0 | 0 | eurogrid x3 |
| B1 | 0 | 0 | 11 | 0 | awilix explicit 2, awilix implicit 3, customer delivery 3, cattrs 3 |
| D1 | 0 | 0 | 0 | 23 | market share 3, seat surplus 3, chatgpt proposal 3, partnership 3, awilix explicit 1, cookie store 3, DAPT 3, CSM 1, Teams 3 |
| all other buckets | 0 | 0 | 0 | 0 | none assigned |
| Total | 3 | 0 | 11 | 23 | 37 |

Reasons:
- A1 (O): reward is exactly 0.8333 in all three, equal to the reference score (TASK-LEVEL.md, summary). All three opened memory; irrelevant to the outcome.
- B1 (I): memory could only help with a fact or convention no source run covers. Awilix: preference part is 0.0 in all 6 read-first failures that ran the test suite (partial-credit parts, O), 0 related runs (corpus coverage), preference 0.0 in 30/30 trials of all arms whether memory was opened or not (TASK-LEVEL.md, paired). Customer delivery and cattrs: near misses (partial 0.949 to 0.989) in the same range as control and run 1 (paired), 0 related runs. Caveat for those two tasks: a generic convention ("document public API, add example") could sit in the unread memory text, so B1 is a task-level inference, not a reading of memory. Need sentences are in the jsonl.
- D1 (U): all remaining trials need a trajectory, verifier log or memory text. Awilix explicit trial P6zn8RP shows tests 0.0 as well as preference 0.0, unlike the other five (tests 0.92 to 0.96), which points to missing output or a broken patch (A7/A4/A3 candidates), not settled.

Not assigned anywhere, on purpose: C1, C3, C4, C5, C6, A3, A7, B6. They are open candidates, not zero counts.

## 4. Per-task table

Opened = read-first opened/3, run 1 opened = run 1 opened/3 (same task), passes are read-first / run 1 / control out of 3.

| Task | Failures | RF opened | R1 opened | Passes RF/R1/ctl | Primary (grade) | Notes |
|---|---|---|---|---|---|---|
| apex market-share | 3 | 3 | 2 | 0/1/0 | D1 (U) | one run 1 pass came without opening; trial RKA3wHY opened at turn 12 of 47 calls (20 calls before) |
| apex seat-surplus | 3 | 1 | 1 | 0/0/0 | D1 (U) | two never-opened trials ran 0.9 and 1.0 min with 4 and 5 tool calls; control (0.9, 1.1 min) and run 1 (1.0, 1.4) show the same early stops (P); the opened trial ran 25 min, 59 calls |
| apex eurogrid | 3 | 3 | 1 | 0/0/0 | A1 (O) | 0.8333 everywhere |
| automationbench marketing | 0 | 1 | 1 | 3/2/2 | passes only | 2 of 3 passes without opening |
| automationbench chatgpt-proposal | 3 | 1 | 1 | 0/0/0 | D1 (U) | partial 0.6 to 0.8 like control (0.6 to 0.8) and run 1; opened trial 7PmQgr3 turn 12 of 78 calls (30 before) |
| automationbench partnership | 3 | 3 | 3 | 0/0/1 | D1 (U) | all three opened at turns 0, 2, 3, partials 0.125, 0.25, 0.25; control had 0.14, 0.38 and the one pass; run 1 0.12, 0.25, 0.38. Opening happened early and outcome did not beat control |
| awilix explicit | 3 | 2 | 0 | 0/0/0 | B1 (I) x2, D1 x1 | opens 0 to 2 with preference still 0.0 |
| awilix implicit | 3 | 2 | 0 | 0/0/0 | B1 (I) x3 | same |
| word2vec | 0 | 3 | 3 | 3/2/0 | passes only | all opened at turn 0, runs of only 8 to 17 tool calls; control 0/3 |
| cattrs | 3 | 1 | 2 | 0/0/0 | B1 (I) x3 | partial 0.95 to 0.99 as in control |
| cookie store | 3 | 2 | 0 | 0/0/1 | D1 (U) | gates 1.0 / 0.5 / 0.75 and tests 0.98 / 0.90 / 0.91: mixed |
| customer delivery | 3 | 1 | 0 | 0/0/0 | B1 (I) x3 | partial 0.989 in all three |
| DAPT | 3 | 3 | 1 | 0/0/0 | D1 (U) | all opened (first open turns 0, 3, 4; runs of 17 to 22 tool calls); partials 0.79, 0.86, 0.79 vs control 0.21, 0.29, 0.71 and run 1 0.43, 0.57, 0.79 (see section 6) |
| EnterpriseOps CSM | 1 | 1 | 0 | 2/2/2 | D1 (U) | the one failure is the one trial that opened (turn 7, 14 calls before); passes 2/2 unopened |
| EnterpriseOps Teams | 3 | 0 | 0 | 0/0/0 | D1 (U) | 1.2 to 1.4 min, 6 to 8 calls, partial 0.75 in every arm (control 3/3, run 1 3/3, P) |

## 5. Access-log findings

Opened rate (strict opens, `opened` field):

| | read-first | run 1 |
|---|---|---|
| all trials | 27/45 (60%) | 15/45 (33%) |
| failed trials | 23/37 (62%) | 13/38 (34%) |
| passed trials | 4/8 (50%) | 2/7 (29%) |

- The nudge nearly doubled the opened rate. It rose on 8 tasks (awilix explicit 0 to 2, awilix implicit 0 to 2, cookie 0 to 2, customer 0 to 1, CSM 0 to 1, DAPT 1 to 3, eurogrid 1 to 3, market share 2 to 3), fell on cattrs (2 to 1) and was equal on the rest. Teams stayed 0 of 3.
- Opened rate is not higher among passes (4/8) than failures (62%): same direction as D132's within-arm comparison, and a confound with task, since the passing trials sit on three tasks (word2vec 3/3 opened, marketing 1/3, CSM 0/2).
- Never opened despite the nudge: 18 trials; 14 failures and 4 passes (marketing 2, CSM 2, all on tasks where control also passes 2 of 3, so those passes did not need memory, P). Of the 14 failures: 6 sit on B1 tasks (awilix 2, cattrs 2, customer 2) where no source supports content, so not opening is not a delivery failure (taxonomy trap 2); 8 remain `C1_candidate` under D1 (seat surplus 2, chatgpt proposal 2, cookie 1, Teams 3). For the Teams and seat-surplus trials the runs ended after 4 to 8 tool calls, and control and run 1 show the same shape, so the stop may be independent of memory. B6 does not explain any of the 14: the arm check passed on all 45 (D132).
- Opened and still failed: 23 failures. Excluding A1 (3) and B1 (5), 15 are D1 `C4_C5_C6_candidate`: market share 3, seat surplus 1, chatgpt 1, partnership 3, awilix explicit 1, cookie 2, DAPT 3, CSM 1 (cookie includes the late-open trial). Whether the agent applied the content (C4/C5/C6) needs the trajectory. The memory text is also needed to rule out B3/B4 for these.
- Timing among opened failures: median first_open_turn 3, median 4 tool calls before the first open (run 1: 3 and 5 across all opened trials; D132 says 2 vs 5 for all opened). 13 of 27 opened trials opened in the first assistant message (turn 0). Opens at turn 9 or later: market share RKA3wHY (12 of 47 calls), chatgpt 7PmQgr3 (12 of 78), cookie 4tWQuo3 (9 of 118), all tagged `late_open_C3_candidate`. C3 needs the turn where the decisive error occurred, which is not in any file here, so none is assigned.
- Paired by task with run 1: the tasks where the nudge produced new opens (awilix x2, cookie, customer, DAPT, CSM) are exactly where run 1 opened least. Outcomes did not move on any of them except DAPT's partial credit, and awilix preference stayed 0.0.
- Word2Vec is the only task where opening plausibly mattered: all 3 read-first trials opened at turn 0 and passed (run 1: opened 3/3, passed 2/3; control 0/3 passed). These are passes, so not classified here.

## 6. Patterns

1. The nudge changed access, not strict outcomes: 8 passes against run 1's 7 and control's 6 (D132, paired CI spans zero). Strict pass counts on the 37 failures are consistent with that.
2. Failures concentrate where memory cannot hold task-specific content (11 B1 plus 3 A1 = 14 of 37) or in tasks with identical signatures in every arm (Teams 0.75, seat surplus early stops, chatgpt proposal 0.6 to 0.8, awilix preference 0.0). Those are weak candidates for any memory effect.
3. DAPT is the one place partial credit moved with opening: mean partial 0.81 read-first (opened 3/3) vs 0.40 control and 0.60 run 1 (opened 1/3), still 0 strict passes. This is exploratory, 3 trials per cell; no strict gain. DAPT's corpus has 35 related runs with no pass (TASK-LEVEL.md), so what the memory holds is unknown.
4. Partnership is the clearest "opened early, did not help" case: 3/3 opened at turns 0 to 3, partials 0.125 to 0.25, not above control.

## 7. What could not be determined, and why

- All C-group assignments (C1 to C7), A3, A7 and B3/B4 for the 23 D1 trials: need trajectories, saved prompts, verifier logs, and the text of run 1's memory. These are on a VM disk on a node that is down (TAXONOMY.md section 6).
- Whether the "opened" trials read content that mattered: the log has paths, not text.
- Whether the B1 assignments for cattrs and customer delivery hide a generic convention in the memory: needs the memory text.
- Per-trial `arm_check` output: not on this host; B6 exclusion rests on D132 and the audit file.
- Why Teams and seat surplus runs stopped after 4 to 8 tool calls.

D1 count per task and reason: market share 3, seat surplus 3, chatgpt proposal 3, partnership 3, cookie store 3, DAPT 3 (trajectory); awilix explicit 1 (workspace: tests 0.0); CSM 1, Teams 3 (trajectory).

## 8. Conflicts and notes against TASK-LEVEL.md

- No contradiction of a task-level verdict. Eurogrid A1 and the B1 flags are used as written.
- TASK-LEVEL.md says awilix "full functional score in 22/30"; in this arm, awilix explicit trial P6zn8RP has tests 0.0 and SHhC9Bm 0.917, so the functional score is not full in 2 of 6 read-first awilix failures. Consistent with 22/30 across arms, but the exception is relevant to bucket choice here.
- TASK-LEVEL.md caveat on B1 for the AutomationBench tasks (shared-preamble matching) is respected: those tasks are not assigned B1.
- Observation not in TASK-LEVEL.md: the memory is a single skill (D134), so "skill name fits headroom" reduces to reference-file names.
