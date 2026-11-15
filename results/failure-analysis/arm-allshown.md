# Failure analysis: ALL-SHOWN arm (fm-tasks-exposure-all)

45 counted trials (the B5 rerun set), 7 passes, 38 failures. Machine-readable twin: `arm-allshown.jsonl` (38 lines). Taxonomy and task facts: `TAXONOMY.md`, `TASK-LEVEL.md` (not contradicted; see the conflicts section).

## 1. Method and evidence available

Evidence used (host only): `summary-fm-tasks-exposure-all.jsonl` and the control, run 1 and none-shown summaries; `partial-credit-fm-tasks-exposure-all.jsonl`; `audit-fm-tasks-exposure-all.txt`; `memory-access-run1.jsonl`; `official/vm/serving-incidents-d136.json`; decision log D133, D136, D137, D139; `official/fm_local/exposure_hermes.py`, `exposure_measure.py`; `amendments-and-deviations.md`.

Not available: trajectories, saved system prompts, verifier logs, the memory text, and the ten set-aside raw stalled trials. Every trajectory-level bucket is therefore D1 unless a task-level fact and a paired comparison support an I-grade. "Attempt" in the jsonl is the order of `agent_started` inside the counted set; it is not the original Harbor attempt index (the ten reruns all sort last in their task).

What the arm is (exposure_hermes.py): HM's normal start of context (MEMORY.md block, skills index) plus the full text of all 13 memory files, in sorted path order, put in the system prompt through `agent.system_prompt`. Guard: at most 100,000 injected tokens. D133 (e2e trial, not counted): 13 of 13 files in the prompt the model received, 81,116 characters, injected estimate 16,148 tokens, first agent request 28,608 tokens. The audit file for this set reports ISSUES none, memory_enabled true on 45/45, effort max on 45/45. `memory_sha256` is the same run 1 digest (`c3d6f31a...`) on all trials. Per-trial exposure checks (`EXPOSURE_MEASURE`, `arm_check`) were run on the VM; their per-trial output is not on this host, so "memory reached the model" is known for the e2e trial (O) and for the set only from D139's "trials ok" (decision-log statement, I).

## 2. Bucket counts per evidence grade

| Bucket | O | P | I | U |
|---|---|---|---|---|
| A1 grader-infeasible (Eurogrid, 3 trials) | 3 | 0 | 0 | 0 |
| B1 no source (awilix explicit 3, implicit 3, customer delivery 3, cattrs 3, cookie store 3) | 0 | 0 | 15 | 0 |
| D1 undeterminable (20 trials) | 0 | 0 | 0 | 20 |
| A5, A6, B6, B8, C1 to C7, A3 | 0 | 0 | 0 | 0 |

Totals: 38 = 3 O + 15 I + 20 U. B1 is grade I because the corpus count is a host fact (O) but that the generated memory lacks the needed fact is inferred (memory text not read). No B8, C4, C5 or C7 assignment is made: each would need the trajectory or per-request token counts.

D1 per task and why: market share 3, seat surplus 2, marketing 2, chatgpt proposal 3, partnership 3, Word2Vec 1, DAPT 3, CSM 1, Teams 2. In all of them the verifier-relevant behaviour (what the agent did with the shown memory) sits in the trajectory on the VM disk. For market share and seat surplus the judge is also task-level A2.

## 3. Per-task table

Passes: all-shown / control / run 1 / none-shown (each of 3 attempts). Memory relevance is grade I (file names in `memory-access-run1.jsonl` opened paths, plus TASK-LEVEL B1); run 1's memory is one skill (`agent-evals/eval-task-families`) with reference files seen opened: family-analysis-mcp, family-workflow-automation, family-swe-repo, family-pcap, failure-modes, paths, contracts, commands. File contents were not read.

| Task | Fails | Passes a/c/r1/n | Partial (all-shown fails) | Bucket | Memory relevant? |
|---|---|---|---|---|---|
| apex market share | 3 | 0/0/1/0 | 0, 0, 0 | D1 (A2 tag) | family-analysis-mcp exists; B1 YES at 50/70%, 3 runs at 30% |
| apex seat surplus | 2 | 1/0/0/0 | 0, 0 | D1 (A2 tag) | same family file; 1 run at 30% |
| apex eurogrid | 3 | 0/0/0/0 | 0.833 x3 | A1 (O) | strict 1 unreachable (oracle 0.833) |
| marketing content gap | 2 | 1/2/2/2 | 0.58, 0.90 | D1 | family-workflow-automation exists; run 1 opened it in 1 of 3 trials |
| chatgpt proposal | 3 | 0/0/0/0 | 0.70, 0.60, 0.80 | D1 | B1 unreliable (shared preamble) |
| partnership contract | 3 | 0/1/0/0 | 0.25, 0.57, 0.375 | D1 | workflow-automation file opened by run 1 in 3 of 3, all failed |
| awilix explicit | 3 | 0/0/0/0 | 0.479, 0.458, 0.479 | B1 (I) | preference gate 0.0 in 3/3 (O); no source for 12.1.0 |
| awilix implicit | 3 | 0/0/0/0 | 0.479, 0.458, 0.479 | B1 (I) | same |
| Word2Vec | 1 | 2/0/2/1 | 0.833 | D1 | swe-repo, contracts, paths exist; run 1 opened them on all 3 trials |
| cattrs | 3 | 0/0/0/2 | 0.987, 0.974, 0.987 | B1 (I) | no source |
| cookie store | 3 | 0/1/0/1 | 0.814 to 0.875, gates 0.75 in 3/3 | B1 (I) | no source (one 30% run) |
| customer delivery | 3 | 0/0/0/0 | 0.995, 0.968, 0.989 | B1 (I) | no source |
| DAPT | 3 | 0/0/0/0 | 0.786 x3 | D1 | family-pcap exists; 35 related runs, none passing |
| CSM | 1 | 2/2/2/3 | 0.75 | D1 | no family file opened by anyone |
| Teams | 2 | 1/0/0/0 | 0.75, 0.75 | D1 | no family file seen |

## 4. Answers to the assigned questions

**(a) Input tokens.** Summed over 45 trials: all-shown 166.5M, control 154.3M (+8%), run 1 155.1M (+7%), none-shown 153.1M (+9%). Per task (mean of 3), all-shown is above control on 12 of 15 tasks and above run 1 on 10 of 15; median task ratio 1.23 against control, 1.21 against run 1. The increase is not uniform: on the heavy patch tasks it is -14% to +22% (awilix explicit +7%, implicit +22%, cattrs +9%, cookie 0%, customer -14%); on the light tasks it is large in relative terms (seat surplus 2.6x, Teams 1.4x, CSM 1.6x, DAPT 1.6x, market share 1.5x, marketing 1.5x), which fits a fixed per-request prefix of about 16k to 28k tokens (D133) multiplied by the request count. The request count is not in the summary, so that reading is I. Relation to failure: failed trials use more input than passed ones (median 2.09M against 0.44M), but the same gap exists in control (1.55M against 0.44M) and run 1 (2.32M against 0.47M), so it measures task difficulty, not the memory. Within task there is no consistent direction: CSM fail 1.38M against passes 0.44M and 0.20M; Teams fail 0.25M and 0.26M against pass 0.38M; marketing fails 0.54M and 0.74M against pass 0.61M. Input tokens are cumulative over requests, so the final context size, the quantity B8 needs, cannot be read from them. B8 is therefore not assignable (D1), not excluded.

**(b) Minutes against limit.** Longest failed trial: customer delivery 50.5 min of 90 (56%); next awilix implicit 45.7 of 90 (51%), chatgpt proposal 15.5 of 30 (52%), awilix explicit 37.6 of 90. None is above 60% of its limit and no trial reached a limit, no AgentTimeout, exceptions null in 45/45. A6 is excluded as a cause for every failure (O: summary timestamps). Total agent time 14.0 h against 12.8 h control (+9%); median trial 15.5 min against 9.6 min control. One difference stands out: trials under 3 minutes number 2 here against 7 in control, 5 in run 1, 5 in none-shown, and all are failures in every arm. Seat surplus has no 1-minute attempt in this arm (11.4, 8.5, 18.0 min against 0.9/20.0/1.1 in control). Observed; why it happens (more engagement, or a length effect) is not determinable from the host.

**(c) The ten stalled trials.** Counted trials are the clean reruns. Evidence: (1) D136 maps nine stall windows (`serving-incidents-d136.json`, D136-1 to D136-9, 2026-11-08 23:44 to 2026-11-09 10:38 PST); (2) ten trials overlapped a stall and all ended AgentTimeoutError, 0 passed (D136, D137); (3) the counted summary has exactly ten trials starting on 2026-11-10 (16:33Z to 20:47Z): partnership, awilix explicit and implicit, Word2Vec, cattrs, cookie store, customer delivery, DAPT, CSM, Teams, one per task, matching the D136 list, and none carries an exception, `model_unavailable` or a missing reward; (4) the window overlap test I ran on all 45 counted trials (agent_started to agent_finished against the nine windows) finds 0 overlaps. So A5 is excluded for every failed counted trial (O for the first set; for the reruns the evidence that serving was clean is D139's "no serving fault", a decision-log statement the host cannot recheck because the rerun's relay logs are on the VM). The raw 5/45 set is not in the summary file. Passes: 5 outside the reruns, 2 inside (CSM, Teams), giving 7. Eight of the ten reruns failed, all in the table above; their durations (4 to 50 min) and token use fall in the range of their first-round siblings, so the reruns do not look different in kind. Limit of this check: the stalls hit the long heavy-context trials (D136's own observation, root cause unknown, 148k-token checkpoint hypothesis only), so the set-aside rule removed those from the original sample and reran them; whether the rerun conditions were comparable cannot be tested here.

**(d) Passes and losses.** All-shown passed: seat surplus 1, marketing 1, Word2Vec 2, CSM 2, Teams 1. Totals: all-shown 7, run 1 7, control 6, none-shown 9. Tasks where all-shown has fewer passes than another arm: marketing (1 against 2, 2, 2), market share (0 against run 1's 1), partnership (0 against control's 1), cookie (0 against control's 1 and none-shown's 1), cattrs (0 against none-shown's 2), CSM (2 against none-shown's 3). Tasks where it has more: seat surplus (1 against 0), Teams (1 against 0), Word2Vec against control (2 against 0). Every difference is one or two passes out of three attempts; D139 already records all paired differences inside the noise. Distraction candidates (C5 or C7, not assigned): marketing, partnership and cookie. They are candidates because a sibling arm passed and the relevant file names exist, nothing more. Counter-signal: DAPT partial is 0.786 in 3 of 3 attempts against 0.40 (control), 0.60 (run 1) and 0.40 (none-shown) means, so the shown memory moved partial credit on a task with a family-pcap file; no strict pass followed.

**(e) Memory relevance per task (grade I).** Run 1's access log, by file name, shows a family file for the APEX tasks (analysis-mcp), the three AutomationBench tasks (workflow-automation, failure-modes), Word2Vec (swe-repo, contracts, paths) and DAPT (pcap). For the five B1 tasks (awilix x2, cattrs, cookie store, customer delivery; Eurogrid is A1 and also has no source) the corpus has no related run at 30, 50 or 70% (cookie store has one at 30%), so nothing task-specific can be in the memory; the missing facts are version, documentation and convention rules (need sentences in the jsonl). CSM and Teams: B1 NO in TASK-LEVEL, no run 1 open of any family file for them; whether the memory holds anything about EnterpriseOps is unknown.

## 5. Patterns

1. 18 of 38 failures sit on tasks where a correct answer is either impossible under the verifier (Eurogrid) or depends on a fact with no corpus source. Showing the memory in full cannot supply a fact the memory never had (I).
2. The cost of showing everything is modest in tokens (+8% summed) and time (+9%) and moves no trial near a time limit.
3. All-shown loses a pass relative to control, run 1 or none-shown on six tasks and gains on three; the net against run 1 is zero (7 and 7).
4. The patch tasks with no source show near-miss partials (cattrs 0.97 to 0.99, customer 0.97 to 0.99, cookie 0.81 to 0.88 with gates 0.75 every time), the same pattern as in every other arm, which supports "preference conventions missing" over "memory harmed".
5. Short 1-minute failures are mostly absent in this arm (2 against 5 to 7), the one clear behavioural difference observable from the host.

## 6. Not determinable and why

All 20 D1 trials, and any statement that the agent read, ignored (C4) or misused (C5) the memory, need the trajectory. B8 needs per-request prompt sizes and the final context size (saved prompts, VM). B6 for the counted set rests on the VM-side checks reported in D139, not on a host file. Which cookie gate fails, which Eurogrid criterion fails, and why Teams stops early are all in verifier or trajectory files on the VM. The original ten raw stalled trials are not on this host.

## 7. Conflicts with TASK-LEVEL.md

None on facts. Two refinements: (1) TASK-LEVEL says awilix functional tests reach 0.958 in 22 of 30 trials; in this arm 2 of 6 awilix trials sit at 0.917 (one more functional test failing), so the ceiling is not universal. (2) TASK-LEVEL notes 14 of 27 failed seat-surplus trials under 3 minutes across arms; in this arm none of the 2 failed trials is under 3 minutes. Pass counts per task for this arm (seat 1, marketing 1, Word2Vec 2, CSM 2, Teams 1) match TASK-LEVEL.
