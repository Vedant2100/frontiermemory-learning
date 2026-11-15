# Failure analysis: PLACEBO arm (fm-tasks-arm-placebo)

45 trials, 4 strict passes, 41 failures. All 45 valid, exception null, model_unavailable false (`results/official/summary-fm-tasks-arm-placebo.jsonl`); audit shows effort max, memory_enabled true in 45, one memory digest (`475f41e7...`) on all 45, ISSUES none (`audit-fm-tasks-arm-placebo.txt`). Machine-readable twin: `arm-placebo.jsonl` (41 lines).

## 1. Method and limits

- Inputs on this host only: summary and partial-credit jsonl for placebo and control, audit, `official/vm/serving-incidents.json`, decisions log D122-D124, amendments B3, TASK-LEVEL.md, `build_placebo.py`, `arm_check.py`. No trajectories, saved prompts, verifier logs or memory-access log (placebo has none); the VM disk is unreachable.
- B1-B4 not assigned (no content to be missing). Any "lesson missing" is by construction, so `need_sentence` states what a real memory would have had to say, and the placebo cannot have said it.
- Paired comparison: every placebo trial against the 3 control trials of the same task (partial credit, minutes, input tokens). Control passes 6/45, placebo 4/45.
- Trial times in the summary are UTC; incident window is PST (14:49:00-15:58:30 PST = 22:49:00-23:58:30 UTC, Nov 6).
- "attempt" in the jsonl is the order of agent_started within the task.

## 2. Bucket counts per evidence grade (41 failures)

| Bucket | O | P | I | U | Total |
|---|---|---|---|---|---|
| A1 grader-infeasible | 3 (eurogrid) | 0 | 2 (cattrs at 76/77) | 0 | 5 |
| A3 task beyond model (incl. spec-gap) | 0 | 0 | 13 | 0 | 13 |
| A7 output not produced | 0 | 0 | 3 (word2vec) | 0 | 3 |
| D1 undeterminable | 0 | 0 | 0 | 20 | 20 |
| A5, A4, A6, B*, C* | 0 | 0 | 0 | 0 | 0 |

No P grade is used as a primary assignment: the paired comparison is used as a "same as control" check (section 4), which does not by itself name a bucket. Grades are not pooled; 21 of 41 carry an inferred bucket and 20 are D1.

## 3. Per-task table

Placebo vs control: partial credit, minutes, input tokens (ratio of the task's 3-trial sums, placebo/control). Pattern = same as control unless stated.

| Task | Placebo fails/3 | Bucket(s) | Grade | Placebo partials | Control partials (pass=1) | Minutes pl / co | In-token ratio | Pattern |
|---|---|---|---|---|---|---|---|---|
| apex market-share | 2 | D1 (A2 tag) | U | 0, 0 (1 pass) | 0, 0, 0 | 4.7, 12.1 / 5.9, 10.3, 19.0 | 0.65 | Same on failures; the placebo pass (11.8 min) is the arm's gain over control, see 4 |
| apex seat-surplus | 2 | D1 (A2, early-stop) | U | 0, 0 (1 pass) | 0, 0, 0 | 1.3, 1.5 / 0.9, 20.0, 1.1 | 0.93 | Same: <2 min failures in both |
| apex eurogrid | 3 | A1 | O | 0.833 x3 | 0.833 x3 | 12.7-14.8 / 14.0-16.1 | 0.82 | Identical |
| marketing gap | 2 | D1 | U | 0.5, 0.909 (1 pass) | 0.545 (2 pass) | 6.7, 12.8 / 5.2-8.9 | 1.40 | Same range; 0.909 trial ran 12.8 min (longest of 6) |
| chatgpt proposal | 3 | D1 | U | 0.6, 0.8, 0.8 | 0.6, 0.7, 0.8 | 8.4-10.5 / 5.4-8.6 | 1.14 | Same |
| partnership | 3 | D1 | U | 0.25 x3 | 0.14, 0.375 (1 pass) | 6.9-10.7 / 4.0-8.9 | 1.80 | Tighter than control (3x 0.25), same scale |
| awilix explicit | 3 | A3 (spec-gap) | I | 0.479, 0.479, 0.458 | 0.479 x3 | 33.7-40.0 / 33.0-46.0 | 0.82 | Same; one trial tests 0.917 vs control 0.958 ceiling |
| awilix implicit | 3 | A3 (spec-gap) | I | 0.458, 0.479, 0.458 | 0.479 x3 | 26.0-36.8 / 28.6-37.7 | 0.94 | Same; two trials tests 0.917 |
| word2vec | 3 | A7 | I | 0, 0, 0 | 0, 0, 0 | 4.4-7.0 / 2.8-5.6 | 2.06 | Identical outcome; placebo used more tokens and minutes |
| cattrs | 3 | A1 x2, A3 x1 | I | 0.987, 0.987, 0.948 | 0.987, 0.987, 0.948 | 26.9-38.9 / 28.5-41.8 | 0.66 | Identical partial multiset |
| cookie store | 3 | A3 (A1 formal) | I | 0.746, 0.715, 0.862 | 0.698, 0.741 (1 pass) | 28.3-40.5 / 28.8-40.0 | 0.93 | Same range; placebo 0/3 vs control 1/3 |
| customer delivery | 3 | A3 (pref near miss) | I | 0.989, 0.984, 0.984 | 0.989, 0.979, 0.984 | 31.9-53.2 / 32.5-54.7 | 0.85 | Same |
| DAPT | 3 | D1 | U | 0.214, 0.571, 0.571 | 0.714, 0.286, 0.214 | 10.2-13.4 / 6.0-11.4 | 0.96 | Same spread |
| EnterpriseOps CSM | 2 | D1 | U | 0.75, 0.75 (1 pass) | 0.75 (2 pass) | 4.7, 5.9 / 4.0-4.8 | 1.48 | Same signature |
| EnterpriseOps Teams | 3 | D1 | U | 0.75 x3 | 0.75 x3 | 1.3-3.2 / 1.4-2.7 | 1.11 | Identical |

Totals over all 45 trials: placebo 772 agent-minutes vs control 769; output tokens 1,866,445 vs 1,866,256; input tokens 134.7M vs 154.3M (the median per-task ratio is 0.94; the totals differ because the high-token tasks happened to run shorter, not a trend). Median per-task time ratio 1.03. No sign of a length or distraction cost at this resolution.

## 4. Questions asked of the arm

(a) Does a placebo failure differ from control's? Not detectably. 13 of 15 tasks have the same partial-credit signature and time scale (table). Differences, all small-n: word2vec used about 2x control's input tokens with the same 0.0 result; partnership placebo partials are all 0.25; 3 of 6 awilix placebo trials have functional tests at 0.917 where all 6 control trials have 0.958 (3/6 vs 0/6, Fisher p about 0.18, not significant); cookie store 0/3 vs 1/3 passes. No evidence for C5, C7 or B8 as a primary bucket; none is excluded either, since the trajectories that would show distraction are missing. No failed placebo trial is near the time limit (longest 53.2 min of 90, customer delivery), so no A6.

(b) Passes control failed. Two of the 4 placebo passes are on tasks where control scored 0/3: apex market-share (Tf5KWr3, 11.8 min) and apex seat-surplus (DpBtPnu, 14.4 min). Both are LLM-judge tasks (A2 YES at task level) with 5/30 and 3/30 passes across all 10 arms, so these are the kind of pass noise expected from a placebo; the passing runs also took the long run profile (seat-surplus passes 11-18 min versus failures under 3 min), so the difference between pass and fail on these tasks tracks effort and run length rather than anything in the memory, but that is a pattern across arms (TASK-LEVEL), not shown for placebo trajectories. The other two passes: marketing gap (hpCftmj, control 2/3) and CSM (S22xRyo, control 2/3). Control passed on partnership (1) and cookie store (1) where placebo did not. Net 4 vs 6.

(c) Serving hang (D122/B3). Window: 14:49:00-15:58:30 PST (22:49-23:58 UTC Nov 6), Ollama hang, hand-restart at 15:56. The affected trial was placebo trial 2, APEX seat-surplus, first calls at 14:49:06; a 14:45:55 background-review cut at the end of trial 1 (hzfPiLs, agent_finished 22:45:57Z) is the suspected trigger (D122, unconfirmed). Per D123/D124 exactly one trial's agent ran during the window; it was set aside (kept on the VM in `fm-tasks-arm-placebo.incident-d122/`) and rerun via `next-recover-d122b.sh`. In the counted summary: the 75-minute gap between hzfPiLs (ends 22:45:57Z) and the next trial XHDd9J6 (starts 00:01:09Z) contains no counted trial, so no remaining counted trial overlaps the window (O, summary times vs `serving-incidents.json`). The seat-surplus trial ZV6kfPM starts 14:24Z Nov 7, after the set's first completion (06:17 PST = 14:17Z, D124) and after every other trial, which fits it being the rerun (I from times; the set-aside original's result is not on this host, so it cannot be compared). That rerun failed (partial 0, 1.5 min), same as control's short seat-surplus trials. Outside the window the recovery check passed: 0 aborts, 1 HTTP 5xx (tool-call parse, retried to 200, D107 type), 0 upstream errors, 19 of 19 client closes at an agent's end (D124); that one 5xx is not attributed to a trial. All 45 summary rows have exception null and model_unavailable false. No A5 assigned.

## 5. Patterns

1. Placebo reproduces control almost row for row. Same partial on eurogrid (0.833), Teams (0.75), cattrs (identical multiset), awilix (preference 0.0), customer delivery (0.98-0.99). That is what a null memory should do and it supports reading the other arms' failures on these tasks as task-side.
2. Word2Vec is the only task where placebo and control are cleanly separated from every memory arm: placebo and control are 0.0 in 6 of 6 trials (the only six 0.0 partials among the 16 failures, TASK-LEVEL), while every real-memory arm scores 0.17-1.0 (partial-credit files). Memory-shaped noise gave no help, so the path/interface content, not the memory format, mattered. Mechanism (missing /workspace/solution.py) is I, not observed.
3. Placebo's 4 passes plus 41 failures are consistent with control noise (6/45); the arm shows no length or distraction cost at the level of summary tokens and minutes.

## 6. What could not be determined, and why

- 20 trials are D1: APEX x4 (judge output only, no criteria detail, A2 unresolved), marketing x2, chatgpt x3, partnership x3, DAPT x3, CSM x2, Teams x3. Needs trajectories and verifier logs (VM disk). Teams is the easiest to settle first (1-3 min runs, 3 of 4 checks).
- The 13 A3 and 5 A1 assignments are inferred from task-level facts plus identical-to-control signatures, not from trial records. A3 for awilix/customer delivery is really a specification gap (the needed fact is not in the instruction); the bucket label fits only because no memory content was available.
- A7 for word2vec rests on pipeline-audit via TASK-LEVEL, not on a workspace listing.
- B6 (placebo exposure): the audit shows memory_enabled in 45 and a single digest; `arm_check.py` checks the memory block and "Reading notes, part 1." in the saved prompt, but per-trial arm-check output and saved prompts are not on this host. Not assessed.
- The set-aside original trial and its outcome.
- Whether the longer prompt changed behaviour (C7 length confound) at trajectory level.

## 7. Conflicts with TASK-LEVEL.md

None on counts: placebo passes (market-share 1, seat-surplus 1, marketing 1, CSM 1), eurogrid 0.8333 x3, and the failed-time maxima agree. Additions rather than conflicts: (1) the six 0.0 Word2Vec partials are exactly the control and placebo trials; (2) TASK-LEVEL's "14 of 27 failed seat-surplus trials under 3 min" includes both placebo failures (1.3, 1.5 min); (3) cattrs 0.987 equals the oracle's 76/77, so those two trials are at reference level.
