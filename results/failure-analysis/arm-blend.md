# Failure analysis: BLEND arm (fm-tasks-arm-blend)

Layer 1 only (host evidence; no trial directories, trajectories, saved prompts, rewrite texts or verifier logs). Companion file: `arm-blend.jsonl` (42 lines, one per failed trial). "Attempt" is the rank of the trial id within its task (ids are random), not run order.

## 1. Method

Sources: `results/official/summary-fm-tasks-arm-blend.jsonl`, `partial-credit-fm-tasks-arm-blend.jsonl`, `blend-report.json`, `audit-fm-tasks-arm-blend.txt`, run 1 and control summary and partial files, `official/vm/serving-incidents*.json`, `official/fm_local/blend_*.py`, `preregistration-arms.md` (B6), decisions D142, D144, D145, `TASK-LEVEL.md`. Rules from `TAXONOMY.md` applied in order. C1 to C3, B6 not applicable (text always shown). Grade O only where a host field shows the bucket's defining fact; grade I where the causal step is reasoned; D1 (grade U) where the defining evidence is on the VM disk.

Arm facts (O): agent `BlendHermes`, `memory_enabled=false` in 45 of 45, effort max, same model as control, 45 of 45 valid, no exception, no `model_unavailable`, first and last agent time 2026-11-11 18:51 to 2026-11-12 10:18 UTC. The audit file's 45 "memory trial without memory digest" issues are expected for this arm (no memory directory by design), not faults.

## 2. Bucket counts per evidence grade (42 failed trials)

| Bucket | O | P | I | U | Trials |
|---|---|---|---|---|---|
| A1 grader-infeasible | 3 | 0 | 0 | 0 | eurogrid x3 |
| B2 arm gave the task nothing | 9 | 0 | 0 | 0 | partnership x3 (excluded), awilix explicit x3 (unchanged), cookie store x3 (unchanged) |
| B1 no source | 0 | 0 | 9 | 0 | awilix implicit, cattrs, customer delivery (rewrite changed, corpus has no related run) |
| D1 undeterminable | 0 | 0 | 0 | 21 | market share 2, seat surplus 3, marketing 3, chatgpt proposal 3, word2vec 3, DAPT 3, CSM 1, Teams 3 |
| A5, A6, B5 to B8, C-group, A3, A4, A7 | 0 | 0 | 0 | 0 | none supported |

Reading of B2 here: it records that the arm's input equalled control's for those 9 trials (blend-report). It does not name the reason the control condition fails; that underlying reason is D1. Half the failures (21 of 42) and all of the "why did the task text not help" questions for the 12 changed tasks stay D1 until trajectories are read.

## 3. Per-task table

Description status from `blend-report.json` (O). Strict n/3 and mean hidden-test share (partial) from the summary and partial files (O). Delta columns are blend minus run 1 and minus control.

| Task | Description | Added sent. / chars | Strict blend / run1 / ctrl | Partial blend (run1, ctrl) | Failed | Bucket |
|---|---|---|---|---|---|---|
| apex market-share | changed | 11 / 533 to 1522 | 1 / 1 / 0 | 0.333 (0.333, 0.000) | 2 | D1 |
| apex seat-surplus | changed | 13 / 524 to 1799 | 0 / 0 / 0 | 0.000 (0.000, 0.000) | 3 | D1 |
| apex eurogrid | changed | 13 / 306 to 1525 | 0 / 0 / 0 | 0.833 (0.833, 0.833) | 3 | A1 O |
| marketing gap | changed | 6 / 963 to 1588 | 0 / 2 / 2 | 0.696 (0.848, 0.848) | 3 | D1 |
| chatgpt proposal | changed | 11 / 1014 to 2411 | 0 / 0 / 0 | 0.600 (0.667, 0.700) | 3 | D1 |
| partnership contract | EXCLUDED (2 rolls failed contract), ran original | none | 0 / 0 / 1 | 0.131 (0.250, 0.506) | 3 | B2 O |
| awilix explicit | UNCHANGED (sha equal) | 0 / 2275 | 0 / 0 / 0 | 0.479 (0.479, 0.479) | 3 | B2 O |
| awilix implicit | changed | 8 / 2248 to 3314 | 0 / 0 / 0 | 0.479 (0.472, 0.479) | 3 | B1 I |
| word2vec | changed (largest) | 34 / 462 to 2666 | 0 / 2 / 0 | 0.833 (0.944, 0.000) | 3 | D1 |
| cattrs | changed | 5 / 1385 to 2066 | 0 / 0 / 0 | 0.965 (0.987, 0.974) | 3 | B1 I |
| cookie store | UNCHANGED (sha equal) | 0 / 3150 | 0 / 0 / 1 | 0.707 (0.721, 0.813) | 3 | B2 O |
| customer delivery | changed | 15 / 2427 to 3994 | 0 / 0 / 0 | 0.980 (0.988, 0.984) | 3 | B1 I |
| DAPT | changed | 24 / 2479 to 3998 | 0 / 0 / 0 | 0.762 (0.595, 0.405) | 3 | D1 |
| CSM 26d1 | changed | 5 / 11295 to 11840 | 2 / 2 / 2 | 0.917 (0.917, 0.917) | 1 | D1 |
| Teams 2725 | changed | 9 / 14000 to 14913 | 0 / 0 / 0 | 0.750 (0.750, 0.750) | 3 | D1 |

Status counts: 12 changed, 2 unchanged (awilix explicit, cookie store), 1 excluded (partnership). Matches the brief and D144. For the 2 unchanged tasks the arm is control (no memory, original text); the model judged the notes useless for them (prompt rule "return the original unchanged"). For partnership the arm also equals control's condition. So 2 of the 14 compared tasks (the unchanged ones) cannot differ from control except by chance, and on them the comparison with run 1 measures run 1's memory against none, not the rewrite.

## 4. Rewrite fidelity (tag, B3-style)

What `blend-report.json` records (O): number of rolls, hashes, character counts and added sentences. Not recorded: what the added sentences say. So "did the rewrite carry a lesson at all" is answerable only as "something was added" (12 tasks), not "the right thing". The contract check guaranteed the original's items survived verbatim and the rewrite was longer than the original; it did not check that added content was correct or relevant.

- Tasks with no corpus source (B1: awilix both, cattrs, customer delivery, eurogrid, apex both at 30% only, cookie store): the added text, if any, came from run 1's notes about other tasks, so it is generic at best (I). The rewrite added 8, 5, 15 and 13 sentences for awilix implicit, cattrs, customer delivery and eurogrid, growth of +47%, +49%, +65% and +398% of the original length for no task-specific source. Outcomes are indistinguishable from run 1 and control on all four (strict 0, partial within 0.02).
- Sizes: word2vec grew 5.8x (462 to 2666 chars, +34 sentences), eurogrid 5.0x, market share 2.9x, seat surplus 3.4x, DAPT 1.6x, customer delivery 1.6x. Big relative growth appears on short originals. Possible distraction (C5, C7, B8) is a lead only; no trajectory shows it.

## 5. Paired comparison with run 1 and control (O arithmetic from host files)

Over the 14 compared tasks (partnership excluded): strict blend 3, run 1 7, control 5 (of 42 each). Mean hidden-test share: blend 0.667, run 1 0.681, control 0.584 (my computation; D145 reports 63%, 65% and 58% over all 15 tasks, and -0.02 vs run 1 over 15; consistent). Delta vs run 1: -0.014 per task over 14. Delta vs control: +0.083 per task over 14.

Strict passes lost versus run 1 (O): marketing gap (2 to 0) and word2vec (2 to 0). Gained: none. Passes kept: CSM 2 (same as both), market share 1 (same as run 1; control 0). Each lost task is 0 of 3 against 2 of 3, Fisher two-sided about 0.4 on its own. Pooled, the 4 lost passes against 6 + 6 trials gives one-sided hypergeometric p about 0.03, but the two tasks were picked after seeing the result, so this is not evidence of harm. The honest reading is: consistent with noise for any single task, a mild signal of lower strict rate overall (3 vs 7), no signal in partial credit (-0.014).

Largest partial changes vs run 1 (all within 3-attempt noise unless noted): DAPT +0.167, marketing -0.152, word2vec -0.111, chatgpt -0.067. The DAPT gain (also +0.357 vs control) is the only partial rise above 0.1 and is a task where the arm still got 0 of 3 strict. Word2vec rises from 0.000 in control to 0.833 (all three attempts exactly 0.8333), so on that task the rewrite plausibly did supply what control lacked (P: paired against control), but fell short of run 1's 0.944 and 2 of 3 passes.

Preregistered bar (B6): hidden tests +0.15 per task over run 1 with p < 0.05, or strict up on at least 3 tasks and down on none. Strict up on 0 tasks and down on 2; hidden tests -0.014 to -0.02. Missed on both halves (O, consistent with D145).

## 6. Tokens and minutes (O, summary files)

Mean per trial over 45: input tokens blend 3.11M, run 1 3.45M, control 3.43M; output tokens 41.6k, 42.8k, 41.5k; agent minutes 16.9, 17.4, 17.1; total 762, 783, 769 minutes. No failed trial reached a time limit (max share: awilix implicit 55.3 of 90 min, 61%). Task-level deltas worth recording (blend vs run 1, minutes): awilix implicit +12.6 (also +10.0 vs control), seat surplus +7.4, DAPT -12.6, customer delivery -5.1, eurogrid -4.6. The awilix implicit increase (input tokens 8.4M vs 6.3M and 6.2M) is the only candidate for a memory-induced cost (C7); it did not hit A6 and the outcome (preference 0.0 in 3 of 3, tests 0.958) matches every other arm, so it did not cost a pass. Customer delivery used about half run 1's input tokens with no outcome change.

## 7. Serving incidents (A5)

`serving-incidents.json` holds one incident (2026-11-06, placebo arm); `serving-incidents-d136.json` holds the all-shown stalls of 2026-11-08/09. Blend ran 2026-11-11 18:51 to 2026-11-12 10:18 UTC; no listed incident overlaps. D145 records one 3.8 s mid-trial abort with the trial finishing normally; the trial is not named on this host and no failed trial shows an exception or `model_unavailable`. A5 supported for 0 of 42.

## 8. Patterns

1. Structure, not mechanism, explains 12 of 42 failures: 3 eurogrid trials are at the grader ceiling (A1 O), and 9 trials ran with no task-specific text (excluded or unchanged), so the arm cannot differ from control there.
2. The strict pass count (3) is lower than run 1 (7) because of two tasks, marketing and word2vec, both with rewritten descriptions. Both are within sibling noise one at a time; word2vec also shows the rewrite beating control on partial credit.
3. The rewrite step added sentences to every task where the corpus has nothing specific (B1), yet outcomes on those tasks match run 1 and control. Generic additions did not move preference-style checks (awilix preference 0.0 in 3 of 3 implicit and 3 of 3 explicit trials; cattrs 76 of 77 twice).
4. The one clear partial-credit gain is DAPT; it did not convert to strict.

## 9. What could not be determined, and why

- Why any of the 21 D1 trials failed (judge verdicts for apex, failed pytest/SQL checks for word2vec, DAPT, CSM, Teams, marketing, chatgpt): needs trajectories and verifier logs on the down VM disk.
- What each rewrite added, whether it was correct, and whether the agent used it (C4, C5, B3 sub-tags, B8): rewrite text is kept in the guest and only counts and hashes are in the repo.
- Whether the lost marketing and word2vec passes are a rewrite effect or noise: only 3 attempts per task and no trajectories.
- Whether the 3.8 s abort affected a failed trial: trial unnamed.
- The 9 B2 trials and 9 B1 trials show the arm-structure bucket, not the underlying task failure (preference gates, grader). For B1 trials grade I because the causal step (nothing task-specific could be in the rewrite) rests on corpus coverage, which `TASK-LEVEL.md` calls approximate.

## 10. Conflicts with TASK-LEVEL.md

None in task facts. Notes: (a) TASK-LEVEL lists blend passes as market share 1 and CSM 2, which matches the summary file. (b) D145 phrases "run 1 7/45, control 6/45" for the 14-task comparison; on 14 tasks control is 5 strict (its one partnership pass drops out), 6 over all 15. This is a reporting nuance, not a conflict with the task file. (c) TASK-LEVEL's seat-surplus observation (many control-style failures under 3 minutes) does not hold for blend: its 3 failed trials ran 10.5 to 17.6 min.
