# Failure analysis: RUN 1 (Hermes /learn memory, standard delivery), set fm-tasks-run1

Scope: 45 trials, 7 passes, 38 failures (memory_sha256 c3d6f31a4...). All 45 valid, exception null, 0 model_unavailable, judge completed 9 of 9 (`summary-fm-tasks-run1.jsonl`, `audit-fm-tasks-run1.txt`: ISSUES none). Machine-readable rows: `arm-run1.jsonl` (attempt = order by agent_started).

## Method

Followed TAXONOMY.md section 4 order. Task-level A1/B1 from TASK-LEVEL.md and `corpus-coverage.json`; trial-level features from summary, partial-credit and `memory-access-run1.jsonl`; serving window overlap against `official/vm/serving-incidents*.json`. No trajectory, saved prompt, verifier log or memory text was available, so an assignment is made only where task-level facts settle it (A1, B1) or where partial-credit parts plus sibling and control pairing support it (one C6, grade I). Everything else is D1 with the missing evidence named. Trial times are UTC in the summaries; the decision log uses PST (UTC-8), checked against run 1's end (18:37 PST = 02:37Z, last trial's finish).

What run 1's memory is, as far as the host can show: one skill, `agent-evals/eval-task-families/SKILL.md` (category agent-evals), plus supporting files (13 files, 62 KB per arm-designs.md; D134: every Hermes generation exports exactly one skill). Reference file names seen in opened_paths (O): `family-analysis-mcp.md`, `family-workflow-automation.md`, `family-swe-repo.md`, `family-pcap.md`, `failure-modes.md`, `paths.md`, `commands.md`, `contracts.md`. Their text is not on this host; names give topics only (I). D106 records that run 1 shows MEMORY.md and its skill on every finished trial (`exposure_measure.py`), so B5/B6 are not supported for any trial (record is a decision-log note, not a per-trial file).

## Bucket counts per evidence grade (primary bucket, 38 failures)

| Bucket | O | P | I | U | Total |
|---|---|---|---|---|---|
| A1 grader-infeasible (Eurogrid) | 3 | 0 | 0 | 0 | 3 |
| B1 no source (awilix x6) | 6 | 0 | 0 | 0 | 6 |
| B1 no source (customer delivery, cattrs, cookie store) | 0 | 0 | 9 | 0 | 9 |
| C6 applied, still failed (Word2Vec) | 0 | 0 | 1 | 0 | 1 |
| D1 undeterminable | 0 | 0 | 0 | 19 | 19 |

No A5, A4, A6, A7, B2-B8, C1-C5, C7 primary. No failed trial hit its time limit (max share of limit: cattrs 53.0 of 90 min, 59%); no incident window overlaps any trial. One caveat on serving: D107's single Ollama 500 (Nov 5 04:18:32 PST = 12:18:32Z, retried with a byte-identical request and answered 200 two seconds later) falls at the end of Eurogrid attempt bCheDat (12:02 to about 12:15Z) and the start of marketing-content 6zkyYb4 (12:18Z); the log says Eurogrid. It does not touch a counted failure's outcome by the log's own account (grade I: timestamp alignment is off by minutes).

## Per-task table

| Task | Fails | Primary | Grade | Opened (fails) | D1 reason or note |
|---|---|---|---|---|---|
| apex-brightpath-market-share | 2 | D1 | U | 2 of 2, early (after 5 of 33 and 5 of 40 calls) | partial exactly 0.0; judge never tested on wrong outputs; need trajectory and memory text. Passing sibling did not open. |
| apex-brightpath-seat-surplus | 3 | D1 | U | 1 of 3 | two trials ended in 1.0 and 1.4 min (4 and 9 calls); cause of early stop unseen |
| apex-eurogrid-curtailment | 3 | A1 | O | 1 of 3 | all 0.8333, as reference |
| marketing-content-gap | 1 | D1 | U | 1 of 1, late (29 of 37 calls) | siblings and 2 of 3 control passed |
| chatgpt-proposal | 3 | D1 | U | 1 of 3 (call 1 of 83) | partial 0.6-0.7, control same range; B1 unreliable per TASK-LEVEL.md |
| partnership-contract | 3 | D1 | U | 3 of 3 | opened at call 44/64, 0/43, 31/57; partials 0.375, 0.125, 0.25 vs control failures 0.375, 0.143 |
| awilix explicit | 3 | B1 | O | 0 of 3 | parts.preference 0.0, no corpus run |
| awilix implicit | 3 | B1 | O | 0 of 3 | same; one trial has tests 0.917 vs 0.958 ceiling (A3-minor tag) |
| word2vec | 1 | C6 | I | 1 of 1 (call 0) | 5 of 6 tests pass; siblings passed |
| cattrs | 3 | B1 | I | 2 of 3 | partial 0.987 each (76/77) |
| cookie store | 3 | B1 | I | 0 of 3 | partials 0.59, 0.72, 0.86; control passed 1 of 3 |
| customer delivery | 3 | B1 | I | 0 of 3 | partial 0.984-0.989 |
| DAPT | 3 | D1 | U | 1 of 3 (call 21 of 30) | partials 0.43, 0.57, 0.79 |
| EnterpriseOps CSM | 1 | D1 | U | 0 of 1 | siblings passed without opening |
| EnterpriseOps Teams | 3 | D1 | U | 0 of 3 | all 0.75, 1.3-1.8 min, same as control and every arm |

D1 count per task: market share 2, seat surplus 3, marketing 1, chatgpt 3, partnership 3, DAPT 3, CSM 1, Teams 3 (19 total). Reasons are in the table and in each row's `evidence`.

## Access-log findings (O unless marked)

- Opened in 15 of 45 trials (reproduced). Failures: 13 of 38 opened (34%). Passes: 2 of 7 opened (29%), both Word2Vec; 5 of 7 passes did not open (reproduced). Opening rate does not differ between failures and passes (small n).
- Within tasks that have mixed outcomes, opening is not associated with passing: market share passes were the non-opened trial (1 of 1 vs 0 of 2 opened); marketing content passes were 2 of 2 non-opened vs the one opened failing; CSM none opened; Word2Vec all three opened (2 pass). Opening probably reflects the agent finding the task hard, so this is a confound, not an effect (I).
- Six tasks never opened memory in any attempt: awilix explicit and implicit, customer delivery, cookie store, Teams, CSM (18 trials, 0 opens). 12 of those 18 trials are B1 tasks (awilix, customer delivery, cookie store). None of the opened file names refers to these tasks' topics (I). Skill-file topics opened map by name to the task: analysis-mcp on APEX, workflow-automation on AutomationBench, swe-repo on Word2Vec and cattrs, pcap on DAPT (I). No wrong-family opens, so C2 is not supported anywhere.
- Timing among the 13 failed trials that opened: early (at most 10 calls before first open, 9 trials); late (more than 50% of calls): marketing 6zkyYb4 (29 of 37, 78%), DAPT bbiW8Po (21 of 30, 70%), partnership SPwVyW5 (44 of 64, 69%) and vBmFpSV (31 of 57, 54%). These are C3 candidates, tagged on the rows, not assigned: whether the error preceded the open needs the trajectory. `first_open_turn` counts turns, `tool_calls_before_first_open` counts calls, so turn and call positions are not interchangeable.
- Relevance of opened skills to headroom (I): workflow-automation and failure-modes for AutomationBench plausibly concern headroom (recipients, wording, contract workflow), but the text is unseen. paths.md/contracts.md on Word2Vec plausibly supplied the missing output path; the Word2Vec contrast (control and placebo 0.0 in 6 of 6; run 1 0.83, 1.0, 1.0) is the one place memory content visibly helped (P).
- Memory costs: opening runs were not longer than sibling non-opened runs on any mixed task (e.g. chatgpt opened 12.7 min/3.27M input tokens vs 8.3 and 7.4 min for siblings, the one exception, and its 83 calls exceed the instruction's ~50 turn budget; 61 and 55 calls for siblings also exceed it). No A6/C7 assignment.

## Patterns

1. 15 of 38 failures (Eurogrid 3, awilix 6, customer delivery 3, cattrs 3) sit on tasks where no run in the corpus relates to the task or the reference fails the verifier. Of these, 6 are O (awilix: preference part 0.0, no corpus run) and 3 O (Eurogrid A1). None of the awilix or customer-delivery trials opened memory.
2. Near misses dominate B1: customer delivery 0.98-0.99, cattrs 0.987, awilix functional at ceiling. Memory could only have helped by carrying the unstated preference; nothing in the corpus holds it.
3. Teams: partial 0.75 in all 3 run 1 attempts, as in control and placebo and all other arms (P), so memory has no visible effect on that task.
4. Partnership: run 1 partials (0.125-0.375) are at or below control failures (0.143, 0.375). All three attempts opened memory. Placebo gave 0.25 x3, so a prompt-presence effect (C7) cannot be excluded or shown; control n=3.
5. Cookie store: control passed 1 of 3 (partial 0.70-1.0); run 1 0 of 3 (0.59-0.86), placebo 0 of 3 (0.72-0.86). B1 is task-level; the paired drop is within noise of n=3.

## What could not be determined, and why

19 D1 trials: need agent trajectories, verifier logs (per-assertion for AutomationBench/EnterpriseOps, per-criterion for APEX) and the saved prompt per request; all on the VM disk on the down node. For no trial can I say what the memory text said; B3 (generation lost it), B4 (generic name: the one skill is named `eval-task-families`, a weak cue, candidate on DAPT's two unopened trials), C1, C4, C5 stay open. The memory-only layer cannot show whether the 15 opens changed behaviour. Per-check preference results for customer delivery, cattrs and cookie store are inferred from partial credit and oracle facts, not read from verifier output.

## Conflicts with TASK-LEVEL.md

None found. Notes: (a) TASK-LEVEL.md says B1 for the three AutomationBench tasks is unreliable; this analysis follows that and does not assign B1 there. (b) Task-level says 14 of 27 failed seat-surplus trials ran under 3 minutes; in run 1, 2 of 3 failures did.
