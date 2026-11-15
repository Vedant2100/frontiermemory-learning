# Failure analysis: Run 4 (fm-tasks-run4, memory_sha256 176db85a...)

Status: layer 1 (no trajectories, no memory text, no memory-access log). Written from the host files only. All 15 tasks x 3 attempts = 45 trials; 37 failed (strict reward below 1).

## Method

- Features per trial from `results/official/summary-fm-tasks-run4.jsonl` and `partial-credit-fm-tasks-run4.jsonl`; minutes are agent_finished minus agent_started; attempts are ordered by agent start time within the task. Serving windows from `official/vm/serving-incidents.json` (D122) and `serving-incidents-d136.json` (D136) were tested for overlap with each trial (timezone-aware): none overlaps any trial in this run.
- Buckets and rules from TAXONOMY.md; task facts from TASK-LEVEL.md (not re-derived). B1 is graded O where the corpus-coverage count and the failing verifier part are both observed; it is a similar-prompt count and approximate. A bucket needing the trajectory or the memory text is D1 with the missing evidence named. I is used only where task-level facts and sibling comparison with the control and run 1 support it.
- Added by amendment A4 (before any run 3 task result) to replace run 2, whose generation timed out at 6 h and exported no memory (D113, D114). Generation size is not in the decision log for run 4 (only run 3's 6 files, 40 KB is); D134 states runs 1, 3 and 4 each export exactly one skill. 45/45 valid, no no-reward reruns, judge 9/9, serving and trial checks ok (D129). Trials ran 2026-11-07 15:05 to 2026-11-08 about 06:30 UTC, outside every listed serving-incident window (D122 is 11-06; D136 starts 2026-11-08 23:44 -08:00, which is after the run 4 trials).

## Bucket counts per evidence grade

| Bucket | Grade | Trials |
|---|---|---|
| A1 | O | 3 |
| B1 | O | 14 |
| C6 | I | 2 |
| D1 | U | 18 |
| total | | 37 |

D1 count per task: apex-brightpath-market-share 1; apex-brightpath-seat-surplus 2; automationbench-marketing-content-gap-analysis 2; automationbench-sales-chatgpt-proposal-customization 3; automationbench-sales-partnership-contract 3; dapt-intrusion-detection-workflow-learning 3; enterpriseops-csm-26d1b04a 1; enterpriseops-teams-2725d17f 3. Reason in every case: no trajectory, saved prompt, verifier log or memory text is on this host (VM disk on nodevcggpu02, down since 2026-11-14 21:00), and run 4 has no memory-access log.

## Per-trial table

| Task | Att | Reward | Partial | In/out tok (k) | Min | Bucket | Grade | Tags |
|---|---|---|---|---|---|---|---|---|
| apex-brightpath-market-share | 2 | 0.00 | 0.000 | 3124/58 | 32.9 | D1 | U | A2(task-level, judge unvalidated) |
| apex-brightpath-seat-surplus | 1 | 0.00 | 0.000 | 131/1 | 1.2 | D1 | U | A2(task-level, judge unvalidated); early-stop(<3 min) |
| apex-brightpath-seat-surplus | 2 | 0.00 | 0.000 | 68/1 | 1.0 | D1 | U | A2(task-level, judge unvalidated); early-stop(<3 min) |
| apex-eurogrid-curtailment | 1 | 0.83 | 0.833 | 1257/17 | 11.0 | A1 | O | A2 |
| apex-eurogrid-curtailment | 2 | 0.83 | 0.833 | 1973/39 | 19.0 | A1 | O | A2 |
| apex-eurogrid-curtailment | 3 | 0.83 | 0.833 | 3322/48 | 23.1 | A1 | O | A2 |
| automationbench-marketing-content-gap-analysis | 2 | 0.00 | 0.000 | 584/17 | 6.2 | D1 | U | attempt-noise-possible |
| automationbench-marketing-content-gap-analysis | 3 | 0.00 | 0.727 | 502/37 | 12.1 | D1 | U | attempt-noise-possible |
| automationbench-sales-chatgpt-proposal-customization | 1 | 0.00 | 0.800 | 1204/19 | 8.1 | D1 | U | B1-unreliable; partial-far |
| automationbench-sales-chatgpt-proposal-customization | 2 | 0.00 | 0.800 | 753/17 | 6.9 | D1 | U | B1-unreliable; partial-far |
| automationbench-sales-chatgpt-proposal-customization | 3 | 0.00 | 0.700 | 853/12 | 5.0 | D1 | U | B1-unreliable; partial-far |
| automationbench-sales-partnership-contract | 1 | 0.00 | 0.250 | 714/10 | 5.2 | D1 | U | paired-loss-candidate-weak(control 1 of 3 passed; run 1 0/3); B1-unreliable |
| automationbench-sales-partnership-contract | 2 | 0.00 | 0.250 | 739/16 | 7.1 | D1 | U | paired-loss-candidate-weak(control 1 of 3 passed; run 1 0/3); B1-unreliable |
| automationbench-sales-partnership-contract | 3 | 0.00 | 0.250 | 676/11 | 4.9 | D1 | U | paired-loss-candidate-weak(control 1 of 3 passed; run 1 0/3); B1-unreliable |
| awilix-release-tier-explicit | 1 | 0.00 | 0.479 | 4491/84 | 32.0 | B1 | O | memory-text-unread(D1 for B3/B4) |
| awilix-release-tier-explicit | 2 | 0.00 | 0.458 | 7182/90 | 36.2 | B1 | O | memory-text-unread(D1 for B3/B4) |
| awilix-release-tier-explicit | 3 | 0.00 | 0.438 | 9954/92 | 35.2 | B1 | O | memory-text-unread(D1 for B3/B4) |
| awilix-release-tier-implicit | 1 | 0.00 | 0.479 | 5703/79 | 30.9 | B1 | O | memory-text-unread(D1 for B3/B4) |
| awilix-release-tier-implicit | 2 | 0.00 | 0.000 | 9755/96 | 38.3 | B1 | O | memory-text-unread(D1 for B3/B4); tests-zero-unexplained(A4/A7/C5 candidates) |
| awilix-release-tier-implicit | 3 | 0.00 | 0.479 | 5009/82 | 29.3 | B1 | O | memory-text-unread(D1 for B3/B4) |
| build-word2vec-pipeline | 2 | 0.00 | 0.833 | 224/7 | 2.8 | C6 | I | memory-text-unread |
| build-word2vec-pipeline | 3 | 0.00 | 0.833 | 622/21 | 7.3 | C6 | I | memory-text-unread |
| cattrs-compositional-changelog | 2 | 0.00 | 0.987 | 11864/90 | 41.5 | B1 | O | memory-text-unread(D1 for B3/B4); near-miss |
| cattrs-compositional-changelog | 3 | 0.00 | 0.987 | 10112/110 | 48.1 | B1 | O | memory-text-unread(D1 for B3/B4); near-miss |
| cookie-store-compositional-changelog | 1 | 0.00 | 0.832 | 12860/126 | 46.6 | B1 | O | A3(tests<1); memory-text-unread(D1 for B3/B4); paired-loss-candidate(control passed 1/3, memory runs 1/3/4 0/9: C5/C7) |
| cookie-store-compositional-changelog | 2 | 0.00 | 0.577 | 9631/116 | 41.5 | B1 | O | A3(tests<1); memory-text-unread(D1 for B3/B4); paired-loss-candidate(control passed 1/3, memory runs 1/3/4 0/9: C5/C7) |
| cookie-store-compositional-changelog | 3 | 0.00 | 0.728 | 8879/92 | 37.0 | B1 | O | A3(tests<1); memory-text-unread(D1 for B3/B4); paired-loss-candidate(control passed 1/3, memory runs 1/3/4 0/9: C5/C7) |
| customer-delivery-contextual-preferences | 1 | 0.00 | 0.984 | 6447/92 | 37.1 | B1 | O | memory-text-unread(D1 for B3/B4); near-miss |
| customer-delivery-contextual-preferences | 2 | 0.00 | 0.989 | 10743/104 | 43.4 | B1 | O | memory-text-unread(D1 for B3/B4); near-miss |
| customer-delivery-contextual-preferences | 3 | 0.00 | 0.995 | 8797/87 | 32.6 | B1 | O | memory-text-unread(D1 for B3/B4); near-miss |
| dapt-intrusion-detection-workflow-learning | 1 | 0.00 | 0.643 | 450/21 | 9.3 | D1 | U | A3-leading-hypothesis(TASK-LEVEL I) |
| dapt-intrusion-detection-workflow-learning | 2 | 0.00 | 0.286 | 651/25 | 12.9 | D1 | U | A3-leading-hypothesis(TASK-LEVEL I) |
| dapt-intrusion-detection-workflow-learning | 3 | 0.00 | 0.857 | 782/36 | 12.9 | D1 | U | A3-leading-hypothesis(TASK-LEVEL I) |
| enterpriseops-csm-26d1b04a | 3 | 0.00 | 0.750 | 236/11 | 4.0 | D1 | U | attempt-noise-possible; 3-of-4-checks-signature |
| enterpriseops-teams-2725d17f | 1 | 0.00 | 0.750 | 170/3 | 1.7 | D1 | U | 3-of-4-checks-signature; early-stop-pattern(median 1.6 min) |
| enterpriseops-teams-2725d17f | 2 | 0.00 | 0.750 | 386/3 | 2.0 | D1 | U | 3-of-4-checks-signature; early-stop-pattern(median 1.6 min) |
| enterpriseops-teams-2725d17f | 3 | 0.00 | 0.750 | 113/2 | 1.4 | D1 | U | 3-of-4-checks-signature; early-stop-pattern(median 1.6 min) |

Exceptions: none in all trials; judge_status completed on all APEX trials; model_unavailable false; audit ISSUES none. Need sentences, evidence lines and sibling notes per trial are in `arm-run4.jsonl`.

## Patterns

1. **Fourteen of 37 failures are B1 with observed task-side evidence** (awilix x6, customer delivery x3, cattrs x2) plus cookie store x3 (preference gates 0.25, 0.5, 0.75, identical to run 1's 0.25, 0.5, 0.75). Corpus coverage is 0 related runs for the first three, 1 run at 30% for cookie store.
2. **Run 4 is the highest-passing memory run (8/45)** and its gains over run 1 are on judge-scored APEX tasks (market-share 2/3 against run 1's 1/3 and control's 0/3; seat-surplus 1/3, a task on which every other counted arm but placebo and all-shown is 0/3) and cattrs (1/3). All APEX passes are under an unvalidated judge (A2), so these are the least reliable of the gains. The seat-surplus pass took 17.9 min against 1.0 and 1.2 min for its two failures: the same split as control and run 1 (long attempts pass, early stops fail).
3. **Word2Vec**: both failures score 0.833, the same value as run 1's failed attempt, while control scores 0.0 in 3 of 3. This is a P-grade sign that the memory changed behaviour (the output file exists and 5 of 6 tests pass), but I-grade as to why the sixth test fails (C6).
4. **csm 2/3 (equal to control and run 1)**: the single failure scores 0.75, the same signature as every csm failure in all arms.
5. **Losses against control**: partnership 0/3 (control 1/3), cookie 0/3 (control 1/3), marketing 1/3 (control 2/3). Marketing run 4 attempt 2 scores 0.0 (6.2 min), a lower partial than any control or run 1 attempt (control 0.545 for the failure, run 1 0.545). With nothing else to separate it, it is D1.
6. **Awilix implicit attempt 2 has tests 0.0** (partial 0.0, 38.3 min, 9.8M tokens), as does one run 3 attempt. Control and run 1 never score 0.0 on awilix (0 of 6 attempts). Two of 6 attempts in runs 3 and 4 against 0 of 6 in control and run 1: candidates A4/A7 (patch broken or absent) or C5, undeterminable here.

## Paired comparison

Memory run passes where control (no memory) fails, grade I that memory caused it:
- **market-share 2/3** (control 0/3, run 1 1/3, run 3 0/3). Judge-scored; the pass needed 12.6 min and 17.1 min, the failure 32.9 min.
- **seat-surplus 1/3** (control 0/3, run 1 0/3, run 3 0/3). 17.9 min versus the two sub-1.5 min failures.
- **cattrs 1/3** (control counted 0/3).
- **Word2Vec 1/3** (control 0/3; run 1 and run 3 2/3 each). Run 4 is the weakest of the three on this task.
The APEX passes tell us the run 4 memory may hold procedure for those tasks (read the chart or table, rounding, report format), but the judge is unvalidated (A2), the attempts are long ones that run for an extended time, and run 1 and run 3 hold the same task at 1/3 and 0/3, so memory content is not demonstrated.

Control passes and run 4 fails (loss candidates, D1): marketing (2/3 to 1/3), partnership (1/3 to 0/3), cookie (1/3 to 0/3). C7 is not supported: no failed trial reached 55% of its limit (TASK-LEVEL section 3), longest 48.1 min (cattrs, 90 min limit) and 46.6 min (cookie store, 90 min limit).

Differences from run 1 (run 1 passes 7: market-share 1, marketing 2, word2vec 2, csm 2; run 4 passes 8): run 4 gains market-share (+1), seat-surplus (+1), cattrs (+1), loses marketing (-1) and word2vec (-1). Implication, grade I: run 4's skill differs from run 1's on cattrs preference (as run 3 does) and possibly on APEX procedure; it holds the Word2Vec interface slightly less reliably (1/3, with both failures at 0.833) than run 1 and run 3.

### enterpriseops-csm: note for this run

csm is 2/3 here, the same as control and run 1. The single failure (attempt 3, 0.75, 4.0 min, 236k/11k tokens) has the same 3-of-4 signature as the failed attempts in the other arms. No difference is observed. See arm-run3.md for the 0/3 anomaly in the other run.

## What could not be determined, and why

- Whether any D1 failure is memory-caused (B3 to B4, C1 to C7): needs the memory text, the skill-open events and trajectories. None is on this host, and no memory-access log exists for this run.
- Why the three judge-scored APEX tasks and three AutomationBench tasks fail: judge unvalidated (A2), AutomationBench B1 counts unreliable (shared preamble matching, TASK-LEVEL section 5).
- Whether B1 tasks (awilix, customer delivery, cattrs) are truly without any lesson in this run's memory: B1 states the corpus has no source, not that the memory is silent; a generic lesson cannot be ruled out without the text.
- Cookie store and word2vec partial-credit differences are consistent with memory effects but the causal step is inferred (I).

## Conflicts with TASK-LEVEL.md

None found. Task-level pass counts per arm for this run agree with the summary files. One reading note: the task file lists cattrs as A1 formal; here cattrs failures at 0.987 are assigned B1 because the single missed check is the preference check (partial 0.987 = 76/77), which is the part the task file says memory could supply.
