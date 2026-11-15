# Failure analysis: EVIDENCE arm (fm-tasks-arm-evidence)

45 trials, 9 strict passes, 36 failures. Format and rules follow `TAXONOMY.md` v1; task facts follow `TASK-LEVEL.md`. Machine-readable twin: `arm-evidence.jsonl` (36 lines). Analyst: evidence arm only; no other arm's bucket was used, control only for pairing.

## 1. Method

Evidence on this host used: `official/summary-fm-tasks-arm-evidence.jsonl`, `partial-credit-...`, `audit-fm-tasks-arm-evidence.txt`, control summary and partial files, `official/fm_local/evidence-runs.json` (what was staged), `official/fm_local/arm_hermes.py`, `arm_logic.py`, `arm_check.py`, `official/vm/serving-incidents*.json`, decisions log D115, D126, D134, D139, D140, the corpus files under `data/corpus/v1.1/inputs/` that the map names, and `results/recency-check.md` (the staging relation).

Steps:
1. For each task I took the list of staged files from `evidence-runs.json` and loaded each with the repo's own `build_corpus_evidence_v5.load_items/outcome_of` (PASS or FAIL from the verifier line).
2. I decided whether a staged record is the **same task** by searching all user messages of the record for task-specific strings (for example `ss_inv`, `Design Review Hub`, `network_stats.csv`, `P47-622334-4396`, `SMB Accounting`, `CookieStore`). This is a text scan, so grade O for "is / is not the same task" and I for what it implies.
3. For same-task PASS records I read the final actions to see whether the missing piece is present.
4. Serving check: evidence ran 2026-11-10 21:13Z to 11-11 12:21Z; the incident files list only Nov 6 and Nov 8-9, so no overlap (O). D140: serving ok, trials ok. No exception, `model_unavailable` false and `valid` true in 45/45 summary rows (O). Longest failed trial is 42.3 min (cattrs, limit 90), so no A6.
5. Audit file: its 45 "memory trial without memory digest" ISSUES are expected for an arm with no generated memory (`memory_enabled=false`); they are not a staging fault.

What this host cannot show: whether any trial opened `/tmp/hermes/records`, what the agent read, the saved prompt per trial, verifier logs (VM disk, node down). So every C-bucket and every "which assertion failed" question is D1 unless a record-level argument makes it moot.

## 2. Important finding about staging (changes how to read this arm)

The relation that built `evidence-runs.json` is `recency_check.py`: a run is "related" if its first user message holds 30% of the task's distinctive tokens **or its opening names the task's repository or family**. The text scan shows that most staged files are other tasks:

| Task | Staged | Same task | Same-task PASS | What the rest are |
|---|---|---|---|---|
| apex market-share | 19 | 0 | 0 | other Brightpath tasks (renewal seat change, approver ranking, win-rate target, Lumea margin); 18 of 19 PASS those |
| apex seat-surplus | 19 | 0 | 0 | same set plus one ITSM policy trial |
| apex eurogrid | 3 | 0 | 0 | EuroGrid headcount-cost task (2 PASS) |
| AB marketing / proposal / partnership | 45 each (same 45 files) | 15 each | 3 / 0 / 0 | the two other AutomationBench tasks |
| Word2Vec | 66 | 9 (exact prompt) plus 2 older-format | 1 (t0212) | 50 files of other command-line tasks |
| cookie store | 1 | 0 | 0 | one EnterpriseOps CSM trial |
| DAPT | 35 | 35 | 0 | none |
| EnterpriseOps CSM | 80 | 17 | 4 | other CSM, Teams, ITSM, HR tasks |
| EnterpriseOps Teams | 44 | 17 | 0 | HR, ITSM, CSM tasks |
| awilix x2, cattrs, customer delivery | 0 | 0 | 0 | none staged, no pointer |

So the "B1 count" in TASK-LEVEL.md (v1.1 at 30/50/70%) and the staged set differ (conflicts in section 7). The arm's pointer also said "tasks like this one" for records that were not this task.

## 3. Bucket counts per evidence grade (36 failures)

| Bucket | O | P | I | U | Total |
|---|---|---|---|---|---|
| B2 memory does not exist (0 records, equals control) | 12 | 0 | 0 | 0 | 12 |
| B1 no source (no same-task record staged) | 9 | 0 | 0 | 0 | 9 |
| A1 grader-infeasible (Eurogrid) | 3 | 0 | 0 | 0 | 3 |
| A3 source exists but holds no passing lesson; capability | 0 | 0 | 11 | 0 | 11 |
| D1 undeterminable | 0 | 0 | 0 | 1 | 1 |
| Total | 24 | 0 | 11 | 1 | 36 |

No trial is assigned a C bucket, B5, B6 or B8, because nothing on this host could support one. That is absence of evidence, not a finding that they did not happen.

A3 here is assigned only because the source holds no same-task passing record, so memory had nothing to supply; the rule that A3 is last (TAXONOMY section 4.2) is met for B-buckets but not for C7 (cost of reading records) and C5 (distraction), which cannot be excluded without trajectories. Hence grade I and the tag `C?-not-excluded`.

## 4. Per-task table

Arm partials and times are listed in start-time order; control is in the same form. "Lesson in source" is the answer to the arm-specific question.

| Task | Arm result (partial) | Control | Staged / same / same-PASS | Lesson in source? | Primary (grade) | D1 count |
|---|---|---|---|---|---|---|
| apex market-share | 0/3 (0, 0, 0) | 0/3 (0,0,0) | 19 / 0 / 0 | No same-task record (B1) | B1 (O) x3 | 0 |
| apex seat-surplus | 0/3 (0, 0, 0) | 0/3 (0,0,0; two control trials under 1.2 min) | 19 / 0 / 0 | No same-task record (B1) | B1 (O) x3 | 0 |
| apex eurogrid | 0/3 (0.833 x3) | 0/3 (0.833 x3) | 3 / 0 / 0 | not needed: ceiling = reference | A1 (O) x3 | 0 |
| AB marketing | 2/3; failure 0.5, 9.1 min | 2/3 (failure 0.545) | 45 / 15 / 3 | **Yes, exists**: PASS record t0002 mails content@ with CGAP-2026-Q1, advocacy 88, decision 74 | D1 (U) x1 | 1 |
| AB proposal | 0/3 (0.8 x3) | 0/3 (0.6, 0.7, 0.8) | 45 / 15 / 0 | **No**: 15 of 15 same-task records FAIL and all contain the competitive-analysis pattern; 7 mention HealthFirst | A3 (I) x3 | 0 |
| AB partnership | 0/3 (0.375, 0.25, 0.5) | 1/3 (0.143, pass, 0.375) | 45 / 15 / 0 | **No** (0 of 15 same-task PASS) | A3 (I) x3 | 0 |
| awilix explicit | 0/3 (0.458, 0.479, 0.479) | 0/3 (0.479 x3) | 0 | n/a, nothing staged | B2 (O) x3 | 0 |
| awilix implicit | 0/3 (0.479 x3) | 0/3 (0.479 x3) | 0 | n/a | B2 (O) x3 | 0 |
| Word2Vec | 3/3 (no failures) | 0/3 (0,0,0) | 66 / 11 / 1 | **Yes**: t0212 PASS has /workspace/solution.py and task_func | none | n/a |
| cattrs | 0/3 (0.961, 0.987, 0.987) | 0/3 (0.987, 0.987, 0.948) | 0 | n/a | B2 (O) x3 | 0 |
| cookie store | 0/3 (0.836, 0.711, 0.75) | 1/3 (0.698, pass, 0.741) | 1 / 0 / 0 | No: the one record is an EnterpriseOps CSM trial | B1 (O) x3 | 0 |
| customer delivery | 0/3 (0.984, 0.989, 0.979) | 0/3 (0.989, 0.979, 0.984) | 0 | n/a | B2 (O) x3 | 0 |
| DAPT | 0/3 (0.714, 0.643, 0.857) | 0/3 (0.714, 0.286, 0.214) | 35 / 35 / 0 | **No passing record**; failing attempts only | A3 (I) x3 | 0 |
| EnterpriseOps CSM | 3/3 (no failures) | 2/3 | 80 / 17 / 4 | see section 5 | none | n/a |
| EnterpriseOps Teams | 1/3; failures 0.75, 0.75 at 1.2 and 1.4 min | 0/3 (0.75 x3, 1.4-2.7 min) | 44 / 17 / 0 | **No** passing same-task record | A3 (I) x2 | 0 |

D1 total: 1 trial (AB marketing). Reason: the source contains the lesson (O), and whether the agent opened, read, or lost it among 45 files (17.9 MB, median 383 KB) is only in the trajectory.

## 5. The passing tasks

- **EnterpriseOps CSM 3/3.** Records were staged: 80 files (6.05 MB), 17 the same task, of which 4 PASS (t0065, t0098, t0252, t0550); 63 are other EnterpriseOps tasks. So memory could not be excluded as a cause, unlike the 0-record tasks. But (a) string presence does not discriminate: all four rubric end values (114B, 2029-09-14, h24x7, 2028-08-15) occur in assistant text of the four PASS records and also of FAIL records t0005, t0075, t0370 (t0041 lacks h24x7), so the records alone do not show the fix; (b) control passed 2/3 and all ten arms pass 19/30, so 3/3 vs 2/3 is inside noise (P); (c) the three arm trials ran 3.5 to 4.2 min with 264k to 596k input tokens, the same range as control's 3.8 to 4.8 min (O). Whether any trial read a record is not known.
- **Teams 1/3.** 44 staged, 17 same task, **0 PASS**; so no staged record could show a passing sequence. The passing attempt used 4.6 min and 799k input tokens against 1.2 to 1.4 min and 138k to 196k for the two failures (O); control failed 3/3 at 1.4 to 2.7 min. Consistent with a longer exploration in the passing trial, but not a read of records (U). The 3 same-task records I read (t0042, t0043, t0154) create the channel and the call and report success, then FAIL; the failing arm trials follow the same chain by shape, partial 0.75.
- **Marketing 2/3.** 3 of 15 same-task records PASS and carry the answer; control also passed 2/3 (P), so the arm cannot be credited. The one failure scored 0.5 (9 of 18) in 9.1 min, longer than the two passes (4.7 and 5.4 min).
- **Word2Vec 3/3.** Not a failure set, but for completeness: one same-family PASS record (t0212) shows `/workspace/solution.py` and `task_func`, the interface the verifier checks (`test_outputs.py` requires `/workspace/solution.py`). Control failed 3/3 with partial 0 and no such file in the prompt. This fits the known headroom (I); nothing here shows the trials opened it.
- **cattrs 0/3, cookie 0/3.** cattrs: nothing staged (B2). Cookie: one unrelated record (B1), so the pointer line was present but led to a different task.

## 6. Patterns

1. **12 of 36 failures (a third) are B2: the arm equalled control by construction** (awilix x2, cattrs, customer delivery). Their partials equal control's within 0.001 except one awilix-explicit trial at 0.458 (O).
2. **12 more are B1 or A1 with no same-task source**: APEX market-share, seat-surplus, cookie store (staged records were other tasks) and Eurogrid (grader ceiling). So 24 of 36 (O) cannot be memory-attributable in this arm.
3. **11 failures are on tasks where same-task records exist but none passes** (proposal 15, partnership 15, DAPT 35, Teams 17 same-task records, all FAIL). The corpus gives failed attempts, which do not say what to do differently. Memory cannot be blamed here on evidence from the source; grade I.
4. **One task where the lesson is in the source** (marketing) fails once at partial 0.5, same as control. Search cost is a candidate (45 files, 15 relevant); not showable.
5. **DAPT** is the only paired partial-credit rise: arm 0.643/0.714/0.857 vs control 0.214/0.286/0.714 (sorted), mean 0.738 vs 0.405 with 35 failing same-task records and 0 passes. Strict stays 0; transfer of procedure is plausible (I), not shown.
6. Records are raw long trajectories (up to 1.4 MB for EuroGrid), so B8 and search failure are candidates for every task with records; nothing on this host shows whether the agent looked (no access log exists for this arm; `memory-access-*.jsonl` covers run 1 and read-first only). Decision log has no per-trial note of record use.

## 7. Conflicts with TASK-LEVEL.md

1. **B1 counts do not equal what was staged.** TASK-LEVEL says apex market-share B1 YES (3/0/0) and seat-surplus (1/0/0), Eurogrid YES (0/0/0), cookie store 1 run at 30%. The arm staged 19, 19, 3 and 1 records for them (via the repo/family clause of `recency_check.py`). The verdicts agree in substance (no same-task record, scan O), but "related runs = 3 / 1 / 0" is not what the arm saw.
2. **Cookie store's "1 related run" is not cookie store**: it is an EnterpriseOps CSM trial (t0591). B1 for cookie is therefore stronger than TASK-LEVEL implies.
3. **AutomationBench B1 "unreliable (shared preamble)"** is partly confirmed: each of the three tasks gets the same 45 files, of which 15 are its own task (marketing 3 PASS, the other two 0 PASS).
4. **Word2Vec**: TASK-LEVEL lists 65 runs at 30% in v1.1; the arm staged 66 (6 PASS by `outcome_of`, TASK-LEVEL says 5). Minor.
5. TAXONOMY section 5 says evidence has "B1, B2 (0 related runs for 8 of 15 tasks)"; the staged set has 4 tasks with 0 files, not 8 (the others got sibling-task files).

## 8. What could not be determined, and why

- Whether any trial opened or read `/tmp/hermes/records` (no trajectories, no access log for this arm).
- Which assertions failed per trial (partial-credit `parts` empty except where absent in the file for AB, APEX and EnterpriseOps tasks).
- Whether the APEX answers were wrong or the judge misgraded (A2 vs capability) and the Teams failing check: final answers and verifier logs are on the VM disk.
- C-bucket assignment for any trial; B5 (copy fault) beyond D140's "trials ok"; B6 (pointer present in the saved prompt) is covered by `arm_check.py` per D126 and D140 but the per-trial report is not on this host.
- Layer 2 (VM) would settle: record opens, search commands, the marketing failure and the five A3 candidates.
