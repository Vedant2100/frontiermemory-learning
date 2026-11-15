# Failure analysis: CONTROL arm (fm-tasks-control)

45 trials, 6 passes, 39 failures. No memory (`memory_enabled=false` in 45/45, `memory_sha256` null; audit-fm-tasks-control.txt). Model qwen3.8:27b-mtp-q4_K_M, effort max, Hermes `LocalHermes`. Per-trial lines are in `arm-control.jsonl`.

## Method

Evidence used (host only): `results/official/summary-fm-tasks-control.jsonl`, `partial-credit-fm-tasks-control.jsonl`, `audit-fm-tasks-control.txt`, `official/vm/serving-incidents*.json` (these sit at the repo root, `official/vm/`, not under `results/`), decisions log D84-D105, D110, D111, and `TASK-LEVEL.md`. No trajectories, workspaces or verifier logs were available, so no bucket here is "observed" except where a field shows it.

Trial-level screens, applied to all 39 failures:
- A5: exception null, `model_unavailable` false in 45/45; no serving incident overlaps (the two incident files start Nov 6, the control ran Nov 4-5 UTC; D105 records 0 Ollama aborts, 0 HTTP 5xx, 0 upstream errors). A5 excluded (O).
- A6: longest failed trial 54.7 of 90 min (customer delivery, 61%); no `AgentTimeout`. A6 excluded for wall clock (O). The 50-turn budget of the three AutomationBench prompts is not visible in wall time (not excluded).
- A7/A4: where `partial > 0` a verifier produced a score from a submitted output, so a missing output is unlikely and a build failure is unlikely, but a partial dependency problem is not excluded.
- A1/A2: per TASK-LEVEL. A1 is primary only for Eurogrid. APEX judge tasks (A2 task-level YES) with partial 0 are not given A2 as primary because there is no evidence the output was otherwise on track.
- A3 is the residual after those exclusions and is graded I, never O. Read every A3 below as "no other cause found in the host evidence", not as an observed capability failure.

## Bucket counts by evidence grade

| Bucket | O | P | I | U | Total |
|---|---|---|---|---|---|
| A1 grader-infeasible | 3 | 0 | 0 | 0 | 3 |
| A3 task beyond model (residual) | 0 | 0 | 27 | 0 | 27 |
| A7 output missing | 0 | 0 | 3 | 0 | 3 |
| D1 undeterminable | 0 | 0 | 0 | 6 | 6 |
| A2, A4, A5, A6, A8 | 0 | 0 | 0 | 0 | 0 |
| Total | 3 | 0 | 30 | 6 | 39 |

D1 count by task: market-share 3, seat-surplus 3. Reason: LLM-judge score 0.0 with no partial parts; separating A2 (judge never tested on wrong outputs), A3, and A7 (no answer posted) needs the agent's final reply and the judge rationale, which are on the VM disk. For seat-surplus, two of three runs lasted 0.9 and 1.1 min (77k and 95k input tokens), an early-stop lead.

## Per-task table

Side = execution-side (A3-A7) or grader-side (A1, A2). "Fails with any memory" is a judgment on headroom (grade I) from TASK-LEVEL and the task source.

| Task | Fail/3 | Partial per attempt (start order) | Minutes (of limit) | Bucket (grade) | Side | Memory outlook |
|---|---|---|---|---|---|---|
| apex market-share | 3 | 0, 0, 0 | 5.9, 10.3, 19.0 (195) | D1 (U) | undetermined; A2 possible | might change (procedure and rounding); numbers need a source, only 3 runs at 30% |
| apex seat-surplus | 3 | 0, 0, 0 | 0.9, 20.0, 1.1 (195) | D1 (U) | undetermined; A2 possible | might change (early stop, procedure); 1 source run at 30% |
| apex eurogrid | 3 | 0.8333 x3 | 16.1, 14.0, 15.9 (195) | A1 (O) | grader | fails with any memory (reference is 0.8333) |
| marketing content gap | 1 | 0.545 (siblings pass) | 8.9 | A3 (I) | execution | might change (recipient and wording rules) |
| chatgpt proposal | 3 | 0.6, 0.7, 0.8 | 5.4, 7.3, 8.6 (30) | A3 (I) | execution | might change (SOP framing); never passes in any arm |
| partnership contract | 2 | 0.143, 0.375 (sibling passes) | 8.9, 4.0 | A3 (I) | execution | might change (workflow is a procedure) |
| awilix explicit | 3 | 0.4792 x3 | 38.4, 33.0, 46.0 (90) | A3 (I) | execution (missing unstated fact) | would pass the preference only if memory states 12.1.0; no corpus source |
| awilix implicit | 3 | 0.4792 x3 | 32.0, 28.6, 37.7 (90) | A3 (I) | execution (missing unstated fact) | same; the instruction never mentions a release tier |
| word2vec | 3 | 0, 0, 0 | 3.0, 5.6, 2.8 (20) | A7 (I) | execution | might change (path and signature are exactly what memory supplies) |
| cattrs | 3 | 0.987, 0.987, 0.948 | 41.8, 35.1, 28.5 (90) | A3 (I) | execution (preference gate) | might change (docs, example, changelog rule) |
| cookie store | 2 | 0.698, 0.741 (sibling passes) | 28.8, 32.9 | A3 (I) | execution (gates 0.5) | might change; passing sibling shows gates are reachable |
| customer delivery | 3 | 0.989, 0.979, 0.984 | 54.7, 32.5, 36.3 (90) | A3 (I) | execution (preferences) | might change (three stated-nowhere conventions); never passes |
| DAPT | 3 | 0.714, 0.286, 0.214 | 6.0, 9.6, 11.4 (90) | A3 (I) | execution | probably fails with any memory (0/35 related runs pass, numeric work) |
| EnterpriseOps CSM | 1 | 0.75 (siblings pass) | 4.8 | A3 (I) | execution | might change |
| EnterpriseOps Teams | 3 | 0.75 x3 | 1.4, 1.6, 2.7 (30) | A3 (I) | execution (one check; early-stop lead) | might change; same 3/4 in 6 of 6 control and run 1 attempts (D110) |

Shares: grader-side as primary = 3/39 (Eurogrid). Execution-side (A3-A7) = 30/39 by exclusion. Undetermined (D1, APEX) = 6/39. If the 6 APEX D1 are counted as possible A2, the grader-side ceiling is 9/39.

## Patterns

1. **Eurogrid is the one grader-bound failure.** 3/3 at exactly 0.8333, the same as the reference.
2. **Deterministic misses (identical partial across attempts).** Awilix explicit and implicit (0.4792 x6, preference 0.0 and tests 0.9583 = oracle ceiling), Teams (0.75 x3), Eurogrid (0.8333 x3), market-share, seat-surplus and word2vec (0.0 x3 each). The Awilix and Teams ones look like one specific unmet requirement per task; these are the failures to compare with memory arms (paired evidence).
3. **Control fails 3/3 on 11 tasks:** market-share, seat-surplus, Eurogrid, chatgpt proposal, both Awilix, word2vec, cattrs, customer delivery, DAPT, Teams. Identical partial across attempts: Eurogrid, both Awilix, Teams, and the three 0.0 tasks. Differing partials: chatgpt (0.6/0.7/0.8), cattrs (0.987/0.987/0.948), customer delivery (0.989/0.979/0.984), DAPT (0.714/0.286/0.214). The memory arms' never-pass tasks (Eurogrid, chatgpt, both Awilix, customer delivery, DAPT) are all control 3/3 failures, so control alone already explains those; memory arms cannot be said to have caused them.
4. **Passing siblings** (marketing 2/3, CSM 2/3, partnership 1/3, cookie store 1/3) rule out A1 for those failures (P) and make run-to-run variation, not task impossibility, the lead.
5. **Short runs:** seat-surplus 0.9 and 1.1 min, Teams 1.4-2.7 min, word2vec under 6 min. Early stops are leads only; nothing shows why they ended.
6. **Near misses:** cattrs and customer delivery score 0.95-0.99 partial but fail strict; the instruction omits the preferences. Memory headroom is in preference conventions, not functionality.

## Not determinable and why

- Trajectory buckets (A3 vs A4/A7 for every partial-credit trial, A7 for word2vec, A2 for APEX): trial directories, workspaces, verifier logs and judge rationales are on the VM disk of the down node. The A3 and A7 grades are I for that reason.
- Which check was missed in Teams, CSM and customer delivery: `parts` is empty for those tasks.
- Word2vec A7: the "no solution.py" statement comes from TASK-LEVEL and pipeline-audit, not from a workspace listing of these trials.
- Why seat-surplus ran about 1 min in two attempts.

## Conflicts with TASK-LEVEL.md

None on numbers: control times, tokens and partials match its per-task figures. Two notes: (a) the serving-incident files live at `official/vm/` (repo root), not `results/official/vm/` as the task brief says; (b) TASK-LEVEL's "failed trials median" values for some tasks combine all arms, so control-only numbers above differ slightly. Neither changes any assignment.
