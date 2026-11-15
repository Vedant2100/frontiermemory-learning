# Failure analysis: Run 3 (fm-tasks-run3, memory_sha256 3fad6cc4...)

Status: layer 1 (no trajectories, no memory text, no memory-access log). Written from the host files only. All 15 tasks x 3 attempts = 45 trials; 41 failed (strict reward below 1).

## Method

- Features per trial from `results/official/summary-fm-tasks-run3.jsonl` and `partial-credit-fm-tasks-run3.jsonl`; minutes are agent_finished minus agent_started; attempts are ordered by agent start time within the task. Serving windows from `official/vm/serving-incidents.json` (D122) and `serving-incidents-d136.json` (D136) were tested for overlap with each trial (timezone-aware): none overlaps any trial in this run.
- Buckets and rules from TAXONOMY.md; task facts from TASK-LEVEL.md (not re-derived). B1 is graded O where the corpus-coverage count and the failing verifier part are both observed; it is a similar-prompt count and approximate. A bucket needing the trajectory or the memory text is D1 with the missing evidence named. I is used only where task-level facts and sibling comparison with the control and run 1 support it.
- Generation 25 min, 6 files, 40 KB, valid (D120). One skill exported (D134: every Hermes generation exports one SKILL.md plus supporting files). 45/45 valid, 0 exceptions, 0 model_unavailable, judge 9/9, audit ISSUES none, serving 0 aborts / 0 5xx (D120). Trials ran 2026-11-06 09:11 to about 23:00 UTC, outside every listed serving-incident window (D122 placebo, D136 all-shown).

## Bucket counts per evidence grade

| Bucket | Grade | Trials |
|---|---|---|
| A1 | O | 3 |
| A3 | I | 2 |
| B1 | O | 12 |
| D1 | U | 24 |
| total | | 41 |

D1 count per task: apex-brightpath-market-share 3; apex-brightpath-seat-surplus 3; automationbench-marketing-content-gap-analysis 2; automationbench-sales-chatgpt-proposal-customization 3; automationbench-sales-partnership-contract 3; build-word2vec-pipeline 1; dapt-intrusion-detection-workflow-learning 3; enterpriseops-csm-26d1b04a 3; enterpriseops-teams-2725d17f 3. Reason in every case: no trajectory, saved prompt, verifier log or memory text is on this host (VM disk on nodevcggpu02, down since 2026-11-14 21:00), and run 3 has no memory-access log.

## Per-trial table

| Task | Att | Reward | Partial | In/out tok (k) | Min | Bucket | Grade | Tags |
|---|---|---|---|---|---|---|---|---|
| apex-brightpath-market-share | 1 | 0.00 | 0.000 | 389/2 | 1.8 | D1 | U | A2(task-level, judge unvalidated); early-stop(<3 min) |
| apex-brightpath-market-share | 2 | 0.00 | 0.000 | 1373/27 | 15.9 | D1 | U | A2(task-level, judge unvalidated) |
| apex-brightpath-market-share | 3 | 0.00 | 0.000 | 2206/49 | 20.2 | D1 | U | A2(task-level, judge unvalidated) |
| apex-brightpath-seat-surplus | 1 | 0.00 | 0.000 | 513/7 | 5.1 | D1 | U | A2(task-level, judge unvalidated) |
| apex-brightpath-seat-surplus | 2 | 0.00 | 0.000 | 184/2 | 1.5 | D1 | U | A2(task-level, judge unvalidated); early-stop(<3 min) |
| apex-brightpath-seat-surplus | 3 | 0.00 | 0.000 | 54/0 | 0.8 | D1 | U | A2(task-level, judge unvalidated); early-stop(<3 min) |
| apex-eurogrid-curtailment | 1 | 0.83 | 0.833 | 1142/23 | 11.5 | A1 | O | A2 |
| apex-eurogrid-curtailment | 2 | 0.83 | 0.833 | 2377/33 | 16.7 | A1 | O | A2 |
| apex-eurogrid-curtailment | 3 | 0.83 | 0.833 | 1589/19 | 10.0 | A1 | O | A2 |
| automationbench-marketing-content-gap-analysis | 1 | 0.00 | 0.538 | 458/15 | 5.3 | D1 | U | paired-loss-candidate |
| automationbench-marketing-content-gap-analysis | 2 | 0.00 | 0.571 | 375/14 | 4.9 | D1 | U | paired-loss-candidate |
| automationbench-sales-chatgpt-proposal-customization | 1 | 0.00 | 0.700 | 836/13 | 5.6 | D1 | U | B1-unreliable; partial-far |
| automationbench-sales-chatgpt-proposal-customization | 2 | 0.00 | 0.700 | 1523/15 | 6.8 | D1 | U | B1-unreliable; partial-far |
| automationbench-sales-chatgpt-proposal-customization | 3 | 0.00 | 0.900 | 1366/18 | 7.7 | D1 | U | B1-unreliable; near-miss |
| automationbench-sales-partnership-contract | 1 | 0.00 | 0.250 | 2214/21 | 9.0 | D1 | U | paired-loss-candidate-weak(control 1 of 3 passed; run 1 0/3); B1-unreliable |
| automationbench-sales-partnership-contract | 2 | 0.00 | 0.000 | 876/13 | 5.6 | D1 | U | paired-loss-candidate-weak(control 1 of 3 passed; run 1 0/3); B1-unreliable |
| automationbench-sales-partnership-contract | 3 | 0.00 | 0.250 | 975/16 | 6.4 | D1 | U | paired-loss-candidate-weak(control 1 of 3 passed; run 1 0/3); B1-unreliable |
| awilix-release-tier-explicit | 1 | 0.00 | 0.479 | 8317/100 | 37.3 | B1 | O | memory-text-unread(D1 for B3/B4) |
| awilix-release-tier-explicit | 2 | 0.00 | 0.479 | 4856/69 | 24.9 | B1 | O | memory-text-unread(D1 for B3/B4) |
| awilix-release-tier-explicit | 3 | 0.00 | 0.458 | 5301/68 | 24.8 | B1 | O | memory-text-unread(D1 for B3/B4) |
| awilix-release-tier-implicit | 1 | 0.00 | 0.000 | 5945/92 | 32.5 | B1 | O | memory-text-unread(D1 for B3/B4); tests-zero-unexplained(A4/A7/C5 candidates) |
| awilix-release-tier-implicit | 2 | 0.00 | 0.458 | 7535/102 | 40.3 | B1 | O | memory-text-unread(D1 for B3/B4) |
| awilix-release-tier-implicit | 3 | 0.00 | 0.479 | 5522/80 | 30.1 | B1 | O | memory-text-unread(D1 for B3/B4) |
| build-word2vec-pipeline | 2 | 0.00 | 0.167 | 452/22 | 7.7 | D1 | U | file-likely-present; A3-candidate |
| cattrs-compositional-changelog | 1 | 0.00 | 0.987 | 4973/63 | 26.0 | B1 | O | memory-text-unread(D1 for B3/B4); near-miss |
| cattrs-compositional-changelog | 2 | 0.00 | 0.987 | 12138/94 | 38.8 | B1 | O | memory-text-unread(D1 for B3/B4); near-miss |
| cookie-store-compositional-changelog | 1 | 0.00 | 0.858 | 10641/86 | 32.2 | B1 | O | A3(tests<1); memory-text-unread(D1 for B3/B4); paired-loss-candidate(control passed 1/3, memory runs 1/3/4 0/9: C5/C7) |
| cookie-store-compositional-changelog | 2 | 0.00 | 0.952 | 7154/83 | 30.1 | A3 | I | C6-candidate; gates-all-passed |
| cookie-store-compositional-changelog | 3 | 0.00 | 0.965 | 6462/99 | 33.8 | A3 | I | C6-candidate; gates-all-passed |
| customer-delivery-contextual-preferences | 1 | 0.00 | 0.989 | 8580/88 | 33.6 | B1 | O | memory-text-unread(D1 for B3/B4); near-miss |
| customer-delivery-contextual-preferences | 2 | 0.00 | 0.984 | 5405/80 | 29.8 | B1 | O | memory-text-unread(D1 for B3/B4); near-miss |
| customer-delivery-contextual-preferences | 3 | 0.00 | 0.995 | 7428/77 | 28.8 | B1 | O | memory-text-unread(D1 for B3/B4); near-miss |
| dapt-intrusion-detection-workflow-learning | 1 | 0.00 | 0.286 | 764/29 | 10.6 | D1 | U | A3-leading-hypothesis(TASK-LEVEL I) |
| dapt-intrusion-detection-workflow-learning | 2 | 0.00 | 0.357 | 993/40 | 12.9 | D1 | U | A3-leading-hypothesis(TASK-LEVEL I) |
| dapt-intrusion-detection-workflow-learning | 3 | 0.00 | 0.643 | 726/20 | 7.6 | D1 | U | A3-leading-hypothesis(TASK-LEVEL I) |
| enterpriseops-csm-26d1b04a | 1 | 0.00 | 0.750 | 445/13 | 4.9 | D1 | U | paired-loss-candidate; 3-of-4-checks-signature |
| enterpriseops-csm-26d1b04a | 2 | 0.00 | 0.750 | 435/11 | 4.8 | D1 | U | paired-loss-candidate; 3-of-4-checks-signature |
| enterpriseops-csm-26d1b04a | 3 | 0.00 | 0.750 | 398/9 | 4.0 | D1 | U | paired-loss-candidate; 3-of-4-checks-signature |
| enterpriseops-teams-2725d17f | 1 | 0.00 | 0.750 | 133/2 | 1.5 | D1 | U | 3-of-4-checks-signature; early-stop-pattern(median 1.6 min) |
| enterpriseops-teams-2725d17f | 2 | 0.00 | 0.750 | 142/2 | 1.4 | D1 | U | 3-of-4-checks-signature; early-stop-pattern(median 1.6 min) |
| enterpriseops-teams-2725d17f | 3 | 0.00 | 0.750 | 207/5 | 2.3 | D1 | U | 3-of-4-checks-signature; early-stop-pattern(median 1.6 min) |

Exceptions: none in all trials; judge_status completed on all APEX trials; model_unavailable false; audit ISSUES none. Need sentences, evidence lines and sibling notes per trial are in `arm-run3.jsonl`.

## Patterns

1. **Twelve of 41 failures are B1 with an observed cause on the task side** (awilix explicit and implicit, customer delivery, cattrs). Source coverage is 0 related runs (corpus-coverage.json) and the verifier part that fails is the preference part in every case (awilix preference 0.0 in 6 of 6; cattrs 0.987 = 76/77). The run 3 memory could not have held these preferences from a source run, unless it carried a generic lesson, which cannot be checked without its text.
2. **Cookie store is the one task where run 3 looks different from every other memory run, grade I.** Preference gates are 0.75, 1.0, 1.0 (mean 0.92) against control 1.0, 0.5, 0.5 (0.67), run 1 0.25, 0.5, 0.75 (0.50), run 4 0.25, 0.5, 0.75 (0.50). In the two attempts with all four gates met the strict failure is in the functional tests (0.904, 0.930). That the gates came from memory content is inferred, not observed. It would mean run 3's skill carries cookie-store conventions (docs, example, mocks, no debug files) that run 1 and run 4 do not. Memory text needed to confirm.
3. **Word2Vec 2/3 (control 0/3)**: both memory runs 1 and 3 reach 2/3, run 4 1/3. Control fails with partial 0.0 in 3 of 3 (no output file, pipeline-audit.md). The one run 3 failure scores 0.167, an outlier below run 1 and run 4's 0.833 failures.
4. **Losses against control, none attributable.** Marketing 1/3 (control 2/3, run 1 2/3, run 4 1/3), partnership 0/3 (control 1/3, run 1 0/3), cookie 0/3 (control 1/3), csm 0/3 (control 2/3). All are at or inside what attempt noise gives with 3 attempts. Run 3 total 4/45 against control 6/45 and run 1 7/45; none of the differences is trial-level evidence of harm.
5. **Early-stop pattern in APEX seat-surplus** (0.8 min, 1.5 min, 5.1 min with 54k, 184k, 513k input tokens) also occurs in control (0.9, 1.1 min) and run 1 (1.4, 1.0 min), so it is not specific to this memory.

## Paired comparison

Memory run passes where control (no memory) fails, grade I that memory caused it:
- **cattrs 1/3** (control counted 0/3; the discarded control passed 1 of 6 per D110). One of the memory-run passes in run 3 and one in run 4, none in run 1. Weak evidence that run 3 and run 4 memories carry the docs/example/changelog preference where run 1 does not.
- **Word2Vec 2/3** (control 0/3, partial 0.0 each): the memory supplies the output path or interface. Run 1 has 2/3 as well, so all three memories carry it.
- **Cookie store gates** (above), a partial-credit gain without a strict pass.

Control passes and run 3 fails (memory-loss candidates, C5/C7/B8, all D1 because trajectories are missing): marketing (2/3 to 1/3), partnership (1/3 to 0/3), cookie (1/3 to 0/3), csm (2/3 to 0/3). C7 (time cost) is not supported: no failed run 3 trial used more than 40.3 min of its limit (awilix implicit 90 min limit), and no trial ran near a limit (TASK-LEVEL section 3).

Differences from run 1 (run 1 passes 7: market-share 1, marketing 2, word2vec 2, csm 2; run 3 passes 4): run 3 loses market-share (1 to 0), marketing (2 to 1), csm (2 to 0) and gains cattrs (0 to 1). Implication, grade I: the memories differ on cattrs and cookie store preference content (run 3 higher), and run 3 is no better than run 1 on the generic-procedure tasks. Market-share is judge-scored with 3 judge names and no separation test (A2), so a 1 to 0 swing there is weak evidence of anything.

### enterpriseops-csm: 0/3 in run 3 against 2/3 in control, run 1 and run 4

Facts (summary and partial-credit files):

| Arm | attempt 1 | attempt 2 | attempt 3 |
|---|---|---|---|
| control | 1.00, 3.8 min, 429k/8k tok | 0.75, 4.8 min, 634k/12k | 1.00, 4.0 min, 217k/10k |
| run 1 | 1.00, 3.6, 466k/9k | 0.75, 3.9, 370k/11k | 1.00, 4.4, 577k/11k |
| run 3 | 0.75, 4.9, 445k/13k | 0.75, 4.8, 435k/11k | 0.75, 4.0, 398k/9k |
| run 4 | 1.00, 5.7, 369k/15k | 1.00, 3.5, 542k/8k | 0.75, 4.0, 236k/11k |

- Every failure in every arm scores exactly 0.75 (3 of 4 checks), so run 3's three failures are the same failure signature the control, run 1 and run 4 show on their failed attempt (P). No new failure mode.
- Token and minute deltas: run 3 median 4.8 min and 435k input against the 9 other attempts of control, run 1 and run 4 (median 4.0 min, 429k). Output tokens 13k, 11k, 9k against 8k to 15k elsewhere. A 0.8 min median delta exists, but the passing attempts in run 4 range 3.5 to 5.7 min, so it does not separate the arms. No exceptions, judge not used, no serving incident overlaps (run 3 trials 2026-11-06 13:19 to 22:18 UTC), audit none.
- Decision log: no csm-specific note for run 3. D120 says run 3 had 45/45 valid, 0 aborts, 0 5xx, so no infrastructure fault is recorded.
- Statistics (descriptive, after the fact): across the other 9 counted/exploratory arms csm passes 19/27 attempts (70%). At that rate 0 of 3 has probability about 0.03, but with 10 arms examined the chance some arm shows 0/3 is about 0.25. With the task's 30-attempt rate of 63% the figures are 0.05 and 0.4.

Reading, grade I: **most consistent with noise**. An infrastructure effect is unsupported (no incident, 0 aborts, normal tokens). A memory-induced effect cannot be excluded because the run 3 memory text is unreachable and could contain a wrong csm lesson (C5/B3d), but nothing observed distinguishes these three trials from the ordinary failing attempt. Run 4 and run 1 with different memory text pass 2/3, and the control with none passes 2/3, so a memory effect would have to be specific to run 3's text. Needed to settle: the run 3 SKILL text for csm and the three trajectories.

## What could not be determined, and why

- Whether any D1 failure is memory-caused (B3 to B4, C1 to C7): needs the memory text, the skill-open events and trajectories. None is on this host, and no memory-access log exists for this run.
- Why the three judge-scored APEX tasks and three AutomationBench tasks fail: judge unvalidated (A2), AutomationBench B1 counts unreliable (shared preamble matching, TASK-LEVEL section 5).
- Whether B1 tasks (awilix, customer delivery, cattrs) are truly without any lesson in this run's memory: B1 states the corpus has no source, not that the memory is silent; a generic lesson cannot be ruled out without the text.
- Cookie store and word2vec partial-credit differences are consistent with memory effects but the causal step is inferred (I).

## Conflicts with TASK-LEVEL.md

None found. Task-level pass counts per arm for this run agree with the summary files. One reading note: the task file lists cattrs as A1 formal; here cattrs failures at 0.987 are assigned B1 because the single missed check is the preference check (partial 0.987 = 76/77), which is the part the task file says memory could supply.
