# Failure analysis: NONE-SHOWN arm (set fm-tasks-exposure-none)

Scope: 45 trials, 9 strict passes, 36 failures. Machine-readable twin: `arm-noneshown.jsonl` (36 lines). Classification follows `TAXONOMY.md` v1 and takes per-task facts from `TASK-LEVEL.md` without re-deriving them. Trial directories, trajectories, saved prompts, verifier logs and memory text are not on this host (VM disk on the down node), so every trajectory-level question is D1 unless stated.

## 1. Method

1. Joined `official/summary-fm-tasks-exposure-none.jsonl`, `partial-credit-fm-tasks-exposure-none.jsonl` and `audit-fm-tasks-exposure-none.txt` with the control and run 1 files (same three files each), per task, attempts ordered by `agent_started`.
2. Arm design from `official/fm_local/exposure_hermes.py` (`exposure=none`: Hermes memory block off, run 1's skills not placed in `$HERMES_HOME/skills`, the whole memory folder still uploaded to `$HERMES_HOME/memories`), `official/vm/run-exposure.sh`, `results/arm-designs.md`, `results/protocol-v4-official.md:58`. Audit file: `memory_enabled=false` 45/45, exception None 45/45, issues none, memory_sha256 (run 1's) on every trial.
3. Bucket order from TAXONOMY section 4. Eurogrid takes A1 at task level. Everything else with a written headroom sentence (TASK-LEVEL "Headroom") reaches B7 by rule order, because B7 precedes A3. **B7 here means "memory-addressable headroom exists and this arm delivered nothing at turn 0". It is the structural default, not a demonstration that memory would have fixed the trial.** The same trials carry a tag `ctrl-analogue:<bucket>` naming the A-bucket the control analyst would most likely give them, and `wf-any` or `wf-maybe` (section 5).
4. Grade rule used: **P** when the trial's partial is inside the range of the control's failed attempts for that task and its agent minutes are within 1/1.5x to 1.5x of the control's range (the trial looks like control). This supports "memory had no visible effect"; it does not prove the agent never opened the memory. **I** otherwise. **O** only for the A1 eurogrid assignment. **U** for D1.
5. Paired comparison: per-task sign-flip test (2^15 enumerations) on mean strict and mean partial against control and run 1, exploratory.

## 2. Bucket counts per grade

| Primary bucket | O | P | I | U | Total |
|---|---|---|---|---|---|
| A1 (eurogrid, task level) | 3 | 0 | 0 | 0 | 3 |
| B7 (arm delivers nothing; headroom exists) | 0 | 23 | 7 | 0 | 30 |
| D1 (cause needs trial directory) | 0 | 0 | 0 | 3 | 3 |
| A5, A4, A6, A7, A8, B5, B6, B8, C1 to C7 | 0 | 0 | 0 | 0 | 0 |
| Total | 3 | 23 | 7 | 3 | 36 |

Grades are never summed across columns in the text below. D1 per task: awilix implicit 1 (trial VrBGMhQ, partial 0.0), Word2Vec 2 (partial 0.8333 against control 0/0/0). Reasons in section 6.

## 3. Per-task table

Partial, minutes and tokens are medians or values from the three files. "Ctrl" is the control's three attempts. Pass counts are strict.

| Task | Passes none / ctrl / run1 | Failed partials (none) | Ctrl partials | Median min none / ctrl | Primary (grade) | Control-analogue and class |
|---|---|---|---|---|---|---|
| apex market-share | 0 / 0 / 1 | 0, 0, 0 | 0, 0, 0 | 9.6 / 10.3 | B7 (P x3) | A2 or A3 undetermined; wf-any |
| apex seat-surplus | 0 / 0 / 0 | 0, 0, 0 | 0, 0, 0 | 1.0 / 1.1 | B7 (P x2, I x1) | A2 or A3 undetermined; wf-any |
| apex eurogrid | 0 / 0 / 0 | 0.8333 x3 | 0.8333 x3 | 26.6 / 15.9 | A1 (O x3) | A1 |
| automation marketing | 2 / 2 / 2 | 0.636 | 0.545 | 5.3 / 7.8 | B7 (I) | A3; wf-maybe |
| automation chatgpt | 0 / 0 / 0 | 0.6, 0.7, 0.6 | 0.6, 0.7, 0.8 | 6.7 / 7.3 | B7 (P x3) | A3; wf-maybe |
| automation partnership | 0 / 1 / 0 | 0, 0, 0.125 | 0.143, 0.375 | 6.6 / 6.4 | B7 (I x3) | A3; wf-maybe |
| awilix explicit | 0 / 0 / 0 | 0.4792 x3 | 0.4792 x3 | 26.6 / 38.4 | B7 (P x3) | A3 (missing fact); wf-any |
| awilix implicit | 0 / 0 / 0 | 0.4792, 0.0, 0.4792 | 0.4792 x3 | 32.0 / 32.0 | B7 (P x2), D1 (U x1) | A3; wf-any |
| Word2Vec | 1 / 0 / 2 | 0.8333 x2 | 0, 0, 0 | 5.1 / 3.0 | D1 (U x2) | A7 or A3; wf-maybe |
| cattrs | 2 / 0 / 0 | 0.987 | 0.987, 0.987, 0.948 | 33.3 / 35.1 | B7 (P) | A3 near miss; wf-maybe |
| cookie store | 1 / 1 / 0 | 0.810, 0.965 | 0.698, 0.741 | 31.1 / 32.9 | B7 (I x2) | A3; wf-maybe |
| customer delivery | 0 / 0 / 0 | 0.989, 0.989, 0.979 | 0.989, 0.979, 0.984 | 36.5 / 36.3 | B7 (P x3) | A3 near miss; wf-maybe |
| DAPT | 0 / 0 / 0 | 0.5, 0.5, 0.214 | 0.714, 0.286, 0.214 | 10.2 / 9.6 | B7 (P x3) | A3; wf-maybe |
| EnterpriseOps CSM | 3 / 2 / 2 | none failed | 0.75 | 4.0 / 4.0 | no failures | n/a |
| EnterpriseOps Teams | 0 / 0 / 0 | 0.75 x3 | 0.75 x3 | 1.5 / 1.6 | B7 (P x3) | A3; wf-maybe |

Totals: none 9, control 6, run 1 7 strict passes. Mean strict per task 0.200 / 0.133 / 0.156. Mean partial per task 0.609 / 0.579 / 0.652. Total agent minutes 781 / 769 / 783; total input tokens 153.1M / 154.3M / 155.1M; median trial minutes 10.2 / 9.6 / 12.7.

## 4. Questions (a) to (e)

**(a) The 9 passes.** Marketing 2 (`Ho8BBjn`, `oR9ejD4`), Word2Vec 1 (`ymHXWLy`), cattrs 2 (`9pDzjTK`, `vh8swaP`), cookie store 1 (`dA3Q74R`), CSM 3 (`fXwN8mN`, `bwpwYi6`, `qWrcEH5`). Against control (marketing 2, partnership 1, cookie store 1, CSM 2) the net is cattrs +2, Word2Vec +1, CSM +1, partnership -1, so +3. Marketing and cookie store are identical to control. CSM 3/3 against 2/3 and 2/3 in control and run 1 is one attempt. The per-task sign-flip test gives mean strict +0.067 versus control (p = 0.50) and +0.044 versus run 1 (p = 0.75); mean partial +0.030 versus control (p = 0.73) and -0.043 versus run 1 (p = 0.23). The arm's 9 equals the evidence arm's 9 and sits in a spread of arm totals of 3 to 9 (control 6, placebo 4, blend 3, read-first 8, all-shown 7, run 1 7; from the decision log D138 to D145), so 9 is the top of the spread, not outside it. The one cell that stands out is cattrs: 2/3 here against 2 passes in the other 27 trials of the other nine arms (Fisher one-sided p about 0.04, uncorrected over 15 tasks and 10 arms, and 0.20 against control's 0/3 alone). The cattrs passes are 77/77 including the preference check, which needs docs, a runnable example and a changelog entry; whether that came from luck, from exploring the disk, or from nothing is not observed (D1). **Word2Vec is the more informative cell** (section 6).

**(b) Failures against control failures.** For 23 of the 33 non-eurogrid failures (the P-graded ones) the profile matches control: identical partial on awilix explicit, awilix implicit (2 of 3), eurogrid, market share, seat surplus, Teams; inside the control range on chatgpt, DAPT, customer delivery, cattrs. Minutes and tokens are in the same band (arm total agent minutes within 2% of control). Differences, all small-n: partnership partials 0, 0, 0.125 against control 0.143 and 0.375 (all three below the control failures; control also holds the only strict pass in 30 trials on that task); cookie store partials 0.81 and 0.965 against control 0.698 and 0.741 (higher, still failing the preference gates); one marketing failure at 0.636 against 0.545; awilix implicit `VrBGMhQ` at 0.0 against 0.4792; Word2Vec 0.8333 x2 against 0/0/0. Heavier runs than control: eurogrid `RJx54qT` 76.5 min, 20.3M input tokens (39% of the 195 min limit, same reward 0.8333) and `qA5hWHq` 26.6 min, 5.0M; seat surplus `7UxmcVS` 32.6 min, 2.3M tokens (control max 20 min). None reaches a time limit (highest share of limit among this arm's failed trials: customer delivery `Hsp24py` 40.6 of 90 min, 45%; eurogrid 39%; awilix implicit 35.1 of 90, 39%), so A6 by wall time is excluded; the 50-turn budget on the three AutomationBench tasks cannot be checked without tool-call counts (D1).

**(c) Did the agent find the memory anyway.** No host evidence either way. There is no access log for this arm (only run 1 and read-first have one), `exposure_measure.py` output for the counted trials is not on the host (it needs the trial directories), the audit file checks config only (`memory_enabled=false` 45/45), and no decision-log entry reports an open. D1 for every trial. Indirect hints, labelled as such: Word2Vec (below) and cattrs. Run 1's own access log shows what the memory contains at file-name level only: one skill with references (`family-swe-repo.md`, `family-workflow-automation.md`, `family-analysis-mcp.md`, `family-pcap.md`, `paths.md`, `contracts.md`, `failure-modes.md`, `commands.md`); no file name suggests awilix, customer delivery or cookie-store content, and run 1 opened nothing in any of its 18 attempts on awilix (2 tasks), cookie store, customer delivery, CSM and Teams.

**(d) Serving incidents.** None overlaps any of the 45 trials. The D136 windows (all-shown stalls) run 2026-11-08 23:44 to 2026-11-09 10:38 PST; this arm's first agent start is 2026-11-09T19:14Z (11:14 PST), so the windows closed 36 minutes earlier; D122 (placebo, Nov 6) is earlier still. All 45 trials: exception null, `model_unavailable` false, `finished` true; decision log D138 records serving ok and trials ok for the set. A5 count 0 (O, from windows against the summary timestamps). Limit: the windows are the logged incidents; the relay log itself is not on this host. Two no-reward trials were rerun by the official rule (D138); the summary keeps the rerun, the originals are on the VM, so which two trials and why is D1.

**(e) Would fail with any memory versus memory might have changed.** Using TASK-LEVEL headroom and corpus coverage (grade I throughout):
- `wf-any` (run 1's memory cannot carry the needed fact): eurogrid (A1, strict 1 unreachable), awilix explicit and implicit (version 12.1.0 appears in no source; B1 YES; preference = 0 in 30/30 trials of the study), market share and seat surplus (task-specific numbers; no related run at 50 or 70%). 15 failures here counting the A1 trials and the one D1 awilix trial: eurogrid 3, awilix 6, market 3, seat 3.
- `wf-maybe` (a general lesson could change the outcome): the three AutomationBench tasks, Word2Vec, DAPT, Teams, and the three preference tasks cattrs, cookie store, customer delivery (no source for those tasks, but the missing item is a convention that a general skill could state). 21 failures.
This split is a reading of headroom, not an outcome. The awilix pair, the near-miss customer delivery and cattrs (partials 0.98 to 0.99), and Teams (identical 0.75, 1.5 min) are the cleanest "same as control" cases.

## 5. Patterns

1. The arm behaves like a second control on most tasks: strict pass count equals control on 11 of 15 tasks (differs on partnership -1, Word2Vec +1, cattrs +2, CSM +1), failed-trial partials and time and token band match control on 23 of 33 non-A1 failures, no serving fault.
2. Differences from control cluster on three tasks where run 1's memory plausibly has content (Word2Vec: `contracts.md`, `paths.md` opened in run 1 passes; cattrs: `commands.md`, `family-swe-repo.md`) and on partnership (lower, not higher). That pattern is consistent with a small amount of disk exploration or with noise; this host cannot separate them.
3. Failed trials in seat surplus: 2 of 3 end in about 1 minute (control 2 of 3 as well), a lead for early stop, not an assignment.
4. Two long outliers in this arm (eurogrid 76.5 min, seat surplus 32.6 min) are the longest agent runs of any arm for those tasks, with no reward change; cause not observed.

## 6. What could not be determined, and why

- Whether any trial opened the memory (C1 to C6 versus B7): needs `exposure-report.json`, trajectories or `exposure_measure.py` output; not on host. All 30 B7 assignments carry `access-unobserved`.
- Word2Vec `xTzHFsx` and `W5uTWto` (partial 0.8333, D1): control scores 0.0 in 3 of 3, run 1 scores 0.833, 1, 1. A produced artifact against none in control is the largest control-versus-arm shift in the failed set, p = 0.05 by Fisher for 3 of 3 non-zero against 0 of 3 (one cell, uncorrected, and the control zeros are themselves unexplained: the pipeline audit says most gate failures wrote no `/workspace/solution.py`, not observed here). Candidate readings: the agent found interface or path information in the disk memory (C-bucket), or ordinary sampling variation in whether `solution.py` is written (A7/A3). Needs the workspace listing and trajectory.
- Awilix implicit `VrBGMhQ` (partial 0.0, D1): functional tests lost, the only 0.0 among the 18 awilix attempts of control, run 1 and this arm (16 at 0.4792, one at 0.4583); build, patch or timeout cause needs the verifier log.
- The content of run 1's memory, so B3 (generation lost it), B4 and C5 cannot be tested.
- Verifier internals: which check fails per trial (`parts` in the partial file is empty for the apex trials and is only informative for awilix and cookie store per TASK-LEVEL).

## 7. Conflicts and notes on TASK-LEVEL.md

- No contradiction of the pass counts, partial ranges or never-pass list: exposure-none = 9 strict passes and the per-task pass counts in TASK-LEVEL section 2 match the summary file.
- Conflict between sources TASK-LEVEL repeats: cattrs entry says one control trial passed 77/77 (`pipeline-audit.md:11`, trial `HJvLDqW`, "counted"), but `summary-fm-tasks-control.jsonl` has 0 cattrs passes among its three trials and `HJvLDqW` appears in no summary file on this host. TASK-LEVEL's own per-arm pass list (control absent for cattrs) agrees with the summary file, not with the pipeline audit sentence.
- Note, not a conflict: the study-wide maximum agent time TASK-LEVEL lists for eurogrid (76.5 min, 20.3M input) is this arm's `RJx54qT`, and the seat-surplus maximum time (32.6 min) is this arm's `7UxmcVS`.
- Taxonomy reading: rule 2 puts B7 before B1, while section 1 puts "did the information exist" before "did it reach the agent". I followed rule 2 and carried B1 as a secondary tag (`B1-no-source`) on 17 B7 trials (awilix 5, customer delivery 3, cattrs 1, cookie store 2, market share 3, seat surplus 3), so a reader who prefers the section 1 order would move those 17 from B7 to B1. Counts per grade would then change; the evidence would not.
