# Task-level facts for the failure analysis

Step 1 (taxonomy section 4, rule 1). Facts per task, written once. Numbers come from `compute.py` (in the session scratchpad, not in the repo) run over `results/official/summary-fm-tasks-*.jsonl` and `partial-credit-fm-tasks-*.jsonl` for the 10 counted arms (control, run1, run3, run4, arm-placebo, arm-readfirst, exposure-all, exposure-none, arm-evidence, arm-blend; 10 arms x 3 attempts = 30 trials per task). Machine-readable twin: `results/failure-analysis/task-level.json`. Evidence grade of every headroom line is I. No trial is classified here.

## Corrections to the taxonomy

- TAXONOMY.md says seven tasks never pass; the summary files give **six** with 0 of 30 (list in section 4 below). The next lowest are partnership contract 1/30, cookie store 2/30 and Teams 2/30. Total passes 65 matches.
- Oracle was measured on all 15 tasks in the Docker guest (decisions log D70, D75, D81, job 305819), and the protocol check list is still unticked (`results/protocol-v4-official.md:72`). Per-task oracle numbers below come from the CPU oracle checks where they exist, and otherwise from maintainers.md plus the decisions log.

## 1. Verdict table

| Task | Verifier | Checks | A1 | A2 | B1 (v1.1: runs at 30/50/70%) | Passes /30 | Never |
|---|---|---|---|---|---|---|---|
| apex-brightpath-market-share | LLM judge | 3 | A1 NO | YES (task-level) | YES (3/0/0) | 5 |  |
| apex-brightpath-seat-surplus | LLM judge | 2 | A1 NO | YES (task-level) | YES (1/0/0) | 3 |  |
| apex-eurogrid-curtailment | LLM judge | 6 | A1 YES | YES (task-level) | YES (0/0/0) | 0 | NEVER |
| automationbench-marketing-content-gap-analysis | hidden tests | 18 | A1 NO | not applicable (no LLM judge) | no (45/45/15) | 15 |  |
| automationbench-sales-chatgpt-proposal-customization | hidden tests | 10 | A1 NO | not applicable (no LLM judge) | no (45/45/15) | 0 | NEVER |
| automationbench-sales-partnership-contract | hidden tests | 8 | A1 NO | not applicable (no LLM judge) | no (45/45/45) | 1 |  |
| awilix-release-tier-explicit | hidden tests | 185 | A1 NO | not applicable (no LLM judge) | YES (0/0/0) | 0 | NEVER |
| awilix-release-tier-implicit | hidden tests | 185 | A1 NO | not applicable (no LLM judge) | YES (0/0/0) | 0 | NEVER |
| build-word2vec-pipeline | hidden tests | 6 | A1 NO | not applicable (no LLM judge) | no (65/9/9) | 14 |  |
| cattrs-compositional-changelog | hidden tests | 77 | A1 YES formal | not applicable (no LLM judge) | YES (0/0/0) | 4 |  |
| cookie-store-compositional-changelog | hidden tests | 1404 | A1 YES formal | not applicable (no LLM judge) | YES (1/0/0) | 2 |  |
| customer-delivery-contextual-preferences | hidden tests | 191 | A1 NO | not applicable (no LLM judge) | YES (0/0/0) | 0 | NEVER |
| dapt-intrusion-detection-workflow-learning | hidden tests | 37 | A1 NO | not applicable (no LLM judge) | no (35/35/35) | 0 | NEVER |
| enterpriseops-csm-26d1b04a | hidden tests | 4 | A1 YES formal | not applicable (no LLM judge) | no (80/34/25) | 19 |  |
| enterpriseops-teams-2725d17f | hidden tests | 4 | A1 YES formal | not applicable (no LLM judge) | no (44/34/34) | 2 |  |

A1 "YES formal" means the reference is below 1; for cattrs, cookie store and the two EnterpriseOps tasks passes were observed, so a strict pass is possible in practice (EnterpriseOps reference replays nothing, so it is uninformative). Eurogrid is the only task where both the reference and every trial sit below 1.

## 2. Per task

### apex-brightpath-market-share

1. **Verifier**: LLM judge; 3 checks; strict pass = reward 1.0 = every rubric criterion judged met (score is a fraction of criteria, with a capped penalty for undesired edits); summary field passed == (reward==1.0) in all 450 trials. All-or-nothing: strict yes (passed=reward==1); the reward itself is a fraction (Eurogrid tops out at 0.8333). Source: data/tasks/frontier-memory/apex-brightpath-market-share/tests/grading_config.json (verifiers list, scoring_config); data/tasks/frontier-memory/apex-brightpath-market-share/tests/grade.py (write_rewards).
2. **Oracle**: 1.0 (maintainers 1; ours via harbor trials regrade of saved reference trials) (measured: yes). A1 NO (reference = 1 under the Opus judge). Source: frontiermemory/docs/maintainers.md:76-83; results/protocol-v4-official.md:52; results/pipeline-audit.md (Grader); D75.
3. **A2**: A2 YES (task-level). Judge: Run with anthropic/claude-opus-5-5 (results/protocol-v4-official.md:52, D74). Documented judge is openai/gpt-5.6-sol (results/protocol-v4-official.md:22; results/pipeline-audit.md Grader table: "CLI pins GPT-5.6 Sol"). The task file grading_config.json names vertex_ai/gemini-2.5-flash (results/pipeline-audit.md). Three different judges are named in the sources. Separation: Only agreement on correct reference answers (reference trials regraded 1, 1, 0.8333 = maintainers; results/protocol-v4-official.md:52 and D75). Agreement on wrong outputs: not measured (same lines). Judge status completed in 30/30 trials (summary field judge_status), so no failed-judge zeros here.
4. **B1**: B1 YES at 50 and 70 pct (none); 3 run(s) at 30 pct. v1.1 counts {"0.3": {"PASS": 2, "FAIL": 1}, "0.5": {"PASS": 0, "FAIL": 0}, "0.7": {"PASS": 0, "FAIL": 0}}. Keys: results/corpus-coverage.json -> "v1.1" -> "tasks" -> "apex-brightpath-market-share" -> "0.3"/"0.5"/"0.7" -> PASS/FAIL (run counts; the key is the overlap threshold).
5. **Passes**: 5/30; per arm (nonzero only) {"run1": 1, "run4": 2, "arm-placebo": 1, "arm-blend": 1}. **Partial among 25 failed**: min 0.0, median 0.0, max 0.0; 0 at >=0.9, 25 at 0; mostly far.
6. **Time**: limit 195 min (data/tasks/frontier-memory/apex-brightpath-market-share/task.toml [agent] timeout_sec); agent minutes all trials median 11.9, max 32.9; failed trials median 11.7, max 32.9; failed at or over limit 0, over 90% 0, over 50% 0; median input/output tokens 1,050,798/20,037 (max input 3,124,457); exceptions none, model_unavailable 0, invalid 0.
7. **Headroom (I)**: I: procedure for reading the chart/segment files, the rounding convention and the report format could come from memory; the three numeric answers are task-specific facts that memory has only if a related run (3 at 30% overlap, no 50%) supplied them.

### apex-brightpath-seat-surplus

1. **Verifier**: LLM judge; 2 checks; strict pass = reward 1.0 = every rubric criterion judged met (score is a fraction of criteria, with a capped penalty for undesired edits); summary field passed == (reward==1.0) in all 450 trials. All-or-nothing: strict yes (passed=reward==1); the reward itself is a fraction (Eurogrid tops out at 0.8333). Source: data/tasks/frontier-memory/apex-brightpath-seat-surplus/tests/grading_config.json (verifiers list, scoring_config); data/tasks/frontier-memory/apex-brightpath-seat-surplus/tests/grade.py (write_rewards).
2. **Oracle**: 1.0 (as above) (measured: yes). A1 NO. Source: frontiermemory/docs/maintainers.md:76-83; results/protocol-v4-official.md:52; D75.
3. **A2**: A2 YES (task-level). Judge: Run with anthropic/claude-opus-5-5 (results/protocol-v4-official.md:52, D74). Documented judge is openai/gpt-5.6-sol (results/protocol-v4-official.md:22; results/pipeline-audit.md Grader table: "CLI pins GPT-5.6 Sol"). The task file grading_config.json names vertex_ai/gemini-2.5-flash (results/pipeline-audit.md). Three different judges are named in the sources. Separation: Only agreement on correct reference answers (reference trials regraded 1, 1, 0.8333 = maintainers; results/protocol-v4-official.md:52 and D75). Agreement on wrong outputs: not measured (same lines). Judge status completed in 30/30 trials (summary field judge_status), so no failed-judge zeros here. Observation: 14 of 27 failed trials ran under 3 minutes while the 3 passes took 11.4-17.9 minutes (summary agent_started/agent_finished).
4. **B1**: B1 YES at 50 and 70 pct (none); 1 run(s) at 30 pct. v1.1 counts {"0.3": {"PASS": 0, "FAIL": 1}, "0.5": {"PASS": 0, "FAIL": 0}, "0.7": {"PASS": 0, "FAIL": 0}}. Keys: results/corpus-coverage.json -> "v1.1" -> "tasks" -> "apex-brightpath-seat-surplus" -> "0.3"/"0.5"/"0.7" -> PASS/FAIL (run counts; the key is the overlap threshold).
5. **Passes**: 3/30; per arm (nonzero only) {"run4": 1, "arm-placebo": 1, "exposure-all": 1}. **Partial among 27 failed**: min 0.0, median 0.0, max 0.0; 0 at >=0.9, 27 at 0; mostly far.
6. **Time**: limit 195 min (data/tasks/frontier-memory/apex-brightpath-seat-surplus/task.toml [agent] timeout_sec); agent minutes all trials median 6.8, max 32.6; failed trials median 1.5, max 32.6; failed at or over limit 0, over 90% 0, over 50% 0; median input/output tokens 672,965/10,663 (max input 3,060,528); exceptions none, model_unavailable 0, invalid 0.
7. **Headroom (I)**: I: procedure (which file/table, how Seat Purchased Surplus and share gaps are defined, rounding) and the reply format could come from memory; the two numbers are task facts, with 1 related run at 30% overlap and none at 50%.

### apex-eurogrid-curtailment

1. **Verifier**: LLM judge; 6 checks; strict pass = reward 1.0 = every rubric criterion judged met (score is a fraction of criteria, with a capped penalty for undesired edits); summary field passed == (reward==1.0) in all 450 trials. All-or-nothing: strict yes (passed=reward==1); the reward itself is a fraction (Eurogrid tops out at 0.8333). expected output is a new slide deck (grading_config metadata expected_output=make_new_slide_deck; tests/golden has Curtailment_Analysis.pptx) Source: data/tasks/frontier-memory/apex-eurogrid-curtailment/tests/grading_config.json (verifiers list, scoring_config); data/tasks/frontier-memory/apex-eurogrid-curtailment/tests/grade.py (write_rewards).
2. **Oracle**: about 0.8333 (maintainers 0.83; ours regraded 0.8333) (measured: yes). A1 YES (reference 0.8333 < 1; strict pass not defined; all 30 trials score exactly 0.8333 = 5 of 6 criteria, O, summary reward). Source: frontiermemory/docs/maintainers.md:76-83 ("APEX Eurogrid scored 0.83 from its LLM judge"); results/protocol-v4-official.md:52; D75.
3. **A2**: A2 YES (task-level). Judge: Run with anthropic/claude-opus-5-5 (results/protocol-v4-official.md:52, D74). Documented judge is openai/gpt-5.6-sol (results/protocol-v4-official.md:22; results/pipeline-audit.md Grader table: "CLI pins GPT-5.6 Sol"). The task file grading_config.json names vertex_ai/gemini-2.5-flash (results/pipeline-audit.md). Three different judges are named in the sources. Separation: Only agreement on correct reference answers (reference trials regraded 1, 1, 0.8333 = maintainers; results/protocol-v4-official.md:52 and D75). Agreement on wrong outputs: not measured (same lines). Judge status completed in 30/30 trials (summary field judge_status), so no failed-judge zeros here. One of 6 criteria is missed by the reference and by all 30 trials; which one was not read (not measured).
4. **B1**: B1 YES (no related run at 30/50/70%). v1.1 counts {"0.3": {"PASS": 0, "FAIL": 0}, "0.5": {"PASS": 0, "FAIL": 0}, "0.7": {"PASS": 0, "FAIL": 0}}. Keys: results/corpus-coverage.json -> "v1.1" -> "tasks" -> "apex-eurogrid-curtailment" -> "0.3"/"0.5"/"0.7" -> PASS/FAIL (run counts; the key is the overlap threshold).
5. **Passes**: 0/30; per arm (nonzero only) none. **Partial among 30 failed**: min 0.8333, median 0.8333, max 0.8333; 0 at >=0.9, 0 at 0; mostly far.
6. **Time**: limit 195 min (data/tasks/frontier-memory/apex-eurogrid-curtailment/task.toml [agent] timeout_sec); agent minutes all trials median 13.7, max 76.5; failed trials median 13.7, max 76.5; failed at or over limit 0, over 90% 0, over 50% 0; median input/output tokens 1,851,248/26,745 (max input 20,328,742); exceptions none, model_unavailable 0, invalid 0.
7. **Headroom (I)**: I: nothing in a strict sense; strict 1 is not reachable even by the reference. Memory could at most supply slide-building procedure for the 5 criteria already met.
8. **Never passes**: yes. Why: grader (grade O). Reference scores 0.8333 and all 30 trials score exactly 0.8333 (summary reward; partial-credit strict/partial); strict 1 unreachable under this verifier (A1). Judge named three ways (A2).

### automationbench-marketing-content-gap-analysis

1. **Verifier**: hidden tests (deterministic end-state assertions over the MCP sidecar dump); 18 checks; strict pass = all scored assertions pass (grade.py: reward is the strict metric task_completed_correctly; partial_credit kept beside it). All-or-nothing: yes strict; partial_credit = fraction (assertions in rubric: 18; partial denominators not verified, possibly fewer scored). Gmail send/not-send assertions to named recipients and bodies. Source: data/tasks/frontier-memory/automationbench-marketing-content-gap-analysis/tests/rubric.json (assertions, 18 entries, none excluded); data/tasks/frontier-memory/automationbench-marketing-content-gap-analysis/tests/grade.py:1-8,120-126.
2. **Oracle**: 1 (AutomationBench 3/3 matched) (measured: yes). A1 NO. Source: D70 (decisions log line 76); D81 line 87 (all 15 match); results/protocol-v4-official.md:72.
3. **A2**: A2 not applicable (no LLM judge). Judge: none: deterministic grader Separation: n/a
4. **B1**: B1 NO (related runs exist at 50%). v1.1 counts {"0.3": {"PASS": 3, "FAIL": 42}, "0.5": {"PASS": 3, "FAIL": 42}, "0.7": {"PASS": 3, "FAIL": 12}}. Keys: results/corpus-coverage.json -> "v1.1" -> "tasks" -> "automationbench-marketing-content-gap-analysis" -> "0.3"/"0.5"/"0.7" -> PASS/FAIL (run counts; the key is the overlap threshold).
5. **Passes**: 15/30; per arm (nonzero only) {"control": 2, "run1": 2, "run3": 1, "run4": 1, "arm-placebo": 1, "arm-readfirst": 3, "exposure-all": 1, "exposure-none": 2, "arm-evidence": 2}. **Partial among 15 failed**: min 0.0, median 0.5714, max 0.9091; 2 at >=0.9, 1 at 0; mostly far.
6. **Time**: limit 30 min (data/tasks/frontier-memory/automationbench-marketing-content-gap-analysis/task.toml [agent] timeout_sec); agent minutes all trials median 6.1, max 12.8; failed trials median 6.7, max 12.8; failed at or over limit 0, over 90% 0, over 50% 0; median input/output tokens 471,043/17,328 (max input 941,890); exceptions none, model_unavailable 0, invalid 0.
7. **Headroom (I)**: I: which recipients to notify and not notify, and the "list only acted-on items" wording rule, are procedure/policy that memory could carry; the instruction also fixes a ~50 tool-turn budget (instruction.md) memory cannot lift.

### automationbench-sales-chatgpt-proposal-customization

1. **Verifier**: hidden tests (deterministic end-state assertions over the MCP sidecar dump); 10 checks; strict pass = all scored assertions pass (grade.py: reward is the strict metric task_completed_correctly; partial_credit kept beside it). All-or-nothing: yes strict; partial_credit = fraction (assertions in rubric: 10; partial denominators not verified, possibly fewer scored). strategy-record assertions (saved, account, finance, completion). Source: data/tasks/frontier-memory/automationbench-sales-chatgpt-proposal-customization/tests/rubric.json (assertions, 10 entries, none excluded); data/tasks/frontier-memory/automationbench-sales-chatgpt-proposal-customization/tests/grade.py:1-8,120-126.
2. **Oracle**: 1 (AutomationBench 3/3 matched) (measured: yes). A1 NO. Source: D70 (decisions log line 76); D81 line 87 (all 15 match); results/protocol-v4-official.md:72.
3. **A2**: A2 not applicable (no LLM judge). Judge: none: deterministic grader Separation: n/a
4. **B1**: B1 NO (related runs exist at 50%). v1.1 counts {"0.3": {"PASS": 3, "FAIL": 42}, "0.5": {"PASS": 3, "FAIL": 42}, "0.7": {"PASS": 0, "FAIL": 15}}. Keys: results/corpus-coverage.json -> "v1.1" -> "tasks" -> "automationbench-sales-chatgpt-proposal-customization" -> "0.3"/"0.5"/"0.7" -> PASS/FAIL (run counts; the key is the overlap threshold).
5. **Passes**: 0/30; per arm (nonzero only) none. **Partial among 30 failed**: min 0.5, median 0.7, max 0.9; 1 at >=0.9, 0 at 0; mostly far.
6. **Time**: limit 30 min (data/tasks/frontier-memory/automationbench-sales-chatgpt-proposal-customization/task.toml [agent] timeout_sec); agent minutes all trials median 7.4, max 15.5; failed trials median 7.4, max 15.5; failed at or over limit 0, over 90% 0, over 50% 1; median input/output tokens 1,578,889/17,248 (max input 3,273,649); exceptions none, model_unavailable 0, invalid 0.
7. **Headroom (I)**: I: the Proposal SOP requirements and stakeholder-finance/account framing are procedure that memory could carry; the instruction points at an SOP sheet the agent can read itself, so the gap is likely execution detail, not a missing fact.
8. **Never passes**: yes. Why: capability or missing policy (undetermined) (grade I). Grader feasible (AutomationBench oracle 3/3), no exceptions, all 30 valid, partial 0.5-0.9 (median 0.7, 1 trial at 0.9); the corpus count at 30/50% (45 runs) is identical across the three AutomationBench tasks, which fits matching the shared prompt preamble rather than the task (B1 unreliable). Trajectories needed.

### automationbench-sales-partnership-contract

1. **Verifier**: hidden tests (deterministic end-state assertions over the MCP sidecar dump); 8 checks; strict pass = all scored assertions pass (grade.py: reward is the strict metric task_completed_correctly; partial_credit kept beside it). All-or-nothing: yes strict; partial_credit = fraction (assertions in rubric: 8; partial denominators not verified, possibly fewer scored). DocuSign envelope assertions (exists, created, recipient, count, subject). Source: data/tasks/frontier-memory/automationbench-sales-partnership-contract/tests/rubric.json (assertions, 8 entries, none excluded); data/tasks/frontier-memory/automationbench-sales-partnership-contract/tests/grade.py:1-8,120-126.
2. **Oracle**: 1 (AutomationBench 3/3 matched) (measured: yes). A1 NO. Source: D70 (decisions log line 76); D81 line 87 (all 15 match); results/protocol-v4-official.md:72.
3. **A2**: A2 not applicable (no LLM judge). Judge: none: deterministic grader Separation: n/a
4. **B1**: B1 NO (related runs exist at 50%). v1.1 counts {"0.3": {"PASS": 3, "FAIL": 42}, "0.5": {"PASS": 3, "FAIL": 42}, "0.7": {"PASS": 3, "FAIL": 42}}. Keys: results/corpus-coverage.json -> "v1.1" -> "tasks" -> "automationbench-sales-partnership-contract" -> "0.3"/"0.5"/"0.7" -> PASS/FAIL (run counts; the key is the overlap threshold).
5. **Passes**: 1/30; per arm (nonzero only) {"control": 1}. **Partial among 29 failed**: min 0.0, median 0.25, max 0.5714; 0 at >=0.9, 4 at 0; mostly far.
6. **Time**: limit 30 min (data/tasks/frontier-memory/automationbench-sales-partnership-contract/task.toml [agent] timeout_sec); agent minutes all trials median 7.1, max 15.4; failed trials median 7.1, max 15.4; failed at or over limit 0, over 90% 0, over 50% 1; median input/output tokens 1,213,334/16,468 (max input 2,599,388); exceptions none, model_unavailable 0, invalid 0.
7. **Headroom (I)**: I: the standard contract workflow (which DocuSign envelope fields, recipients, Salesforce updates) is exactly a procedure memory could supply; the instruction is a 2-line request with no steps.

### awilix-release-tier-explicit

1. **Verifier**: hidden tests plus a deterministic preference gate (regex/subprocess on the submitted model.patch); no LLM judge; 185 checks; strict pass = 161 regression + 23 functional (1 skipped) + 1 preference gate: root package.json must go 12.0.5 -> 12.1.0 (one preference gate; counts 184 cases + gate). All-or-nothing: yes strict (all functional, regression and preference checks). Source: data/tasks/frontier-memory/awilix-release-tier-explicit/tests/user_preference_verifier.py:27-47; data/tasks/frontier-memory/awilix-release-tier-explicit/tests/preference-verifier.md; results/awilix-release-tier-explicit-oracle-check-summary.md (Results).
2. **Oracle**: 1 (184/184, preference pass) (measured: yes). A1 NO. Source: results/awilix-release-tier-explicit-oracle-check-summary.md (job 303256); D81.
3. **A2**: A2 not applicable (no LLM judge). Judge: none: deterministic grader Separation: n/a
4. **B1**: B1 YES (no related run at 30/50/70%). v1.1 counts {"0.3": {"PASS": 0, "FAIL": 0}, "0.5": {"PASS": 0, "FAIL": 0}, "0.7": {"PASS": 0, "FAIL": 0}}. Keys: results/corpus-coverage.json -> "v1.1" -> "tasks" -> "awilix-release-tier-explicit" -> "0.3"/"0.5"/"0.7" -> PASS/FAIL (run counts; the key is the overlap threshold).
5. **Passes**: 0/30; per arm (nonzero only) none. **Partial among 30 failed**: min 0.0, median 0.4792, max 0.4792; 0 at >=0.9, 1 at 0; mostly far. Parts keys: ['preference', 'tests'].
6. **Time**: limit 90 min (data/tasks/frontier-memory/awilix-release-tier-explicit/task.toml [agent] timeout_sec); agent minutes all trials median 33.9, max 46.0; failed trials median 33.9, max 46.0; failed at or over limit 0, over 90% 0, over 50% 1; median input/output tokens 7,199,922/89,431 (max input 11,367,011); exceptions none, model_unavailable 0, invalid 0.
7. **Headroom (I)**: I: the preference (an "internal release tier 7" change bumps the root version to 12.1.0) is a fact/convention that memory could supply; instruction.md states only "Internal release tier: 7" and never the target version.
8. **Never passes**: yes. Why: missing preference fact, no source (grade O (that preference gate fails) / I (why)). partial-credit parts: preference = 0.0 in 30/30 trials (O); functional tests at full score (0.958 = 23/24 with the skip counted as not passed, same ceiling as the passing oracle) in 22/30. The oracle passes. Needed fact (version 12.1.0) is absent from the instruction; corpus holds no related run (B1).

### awilix-release-tier-implicit

1. **Verifier**: hidden tests plus a deterministic preference gate (regex/subprocess on the submitted model.patch); no LLM judge; 185 checks; strict pass = same as explicit: 161 + 23 (+1 skipped) + 1 preference gate (version bump 12.1.0). All-or-nothing: yes strict (all functional, regression and preference checks). Source: data/tasks/frontier-memory/awilix-release-tier-implicit/tests/user_preference_verifier.py; data/tasks/frontier-memory/awilix-release-tier-implicit/tests/preference-verifier.md; results/awilix-release-tier-implicit-oracle-check-summary.md.
2. **Oracle**: 1 (184/184, preference pass) (measured: yes). A1 NO. Source: results/awilix-release-tier-implicit-oracle-check-summary.md (job 303255); D81.
3. **A2**: A2 not applicable (no LLM judge). Judge: none: deterministic grader Separation: n/a
4. **B1**: B1 YES (no related run at 30/50/70%). v1.1 counts {"0.3": {"PASS": 0, "FAIL": 0}, "0.5": {"PASS": 0, "FAIL": 0}, "0.7": {"PASS": 0, "FAIL": 0}}. Keys: results/corpus-coverage.json -> "v1.1" -> "tasks" -> "awilix-release-tier-implicit" -> "0.3"/"0.5"/"0.7" -> PASS/FAIL (run counts; the key is the overlap threshold).
5. **Passes**: 0/30; per arm (nonzero only) none. **Partial among 30 failed**: min 0.0, median 0.4792, max 0.4792; 0 at >=0.9, 3 at 0; mostly far. Parts keys: ['preference', 'tests'].
6. **Time**: limit 90 min (data/tasks/frontier-memory/awilix-release-tier-implicit/task.toml [agent] timeout_sec); agent minutes all trials median 32.2, max 55.3; failed trials median 32.2, max 55.3; failed at or over limit 0, over 90% 0, over 50% 2; median input/output tokens 5,777,388/87,627 (max input 12,110,205); exceptions none, model_unavailable 0, invalid 0.
7. **Headroom (I)**: I: same version-bump preference, but the implicit instruction does not even mention a release tier (grep finds no "release tier" in instruction.md), so only memory can supply it.
8. **Never passes**: yes. Why: missing preference fact, no source (grade O / I). preference = 0.0 in 30/30 (O); full functional score in 22/30; instruction does not mention a release tier at all; oracle passes; B1 YES.

### build-word2vec-pipeline

1. **Verifier**: hidden tests; 6 checks; strict pass = all 6 pytest cases pass (test.sh writes reward 1 only on pytest exit 0). All-or-nothing: yes. Source: data/tasks/frontier-memory/build-word2vec-pipeline/tests/test.sh:18-31; data/tasks/frontier-memory/build-word2vec-pipeline/tests/test_outputs.py (6 test_ functions); results/word2vec-openhands/oracle-check-summary.md (6 cases) cited by results/history.md:320.
2. **Oracle**: 1 (6/6) (measured: yes). A1 NO. Source: results/history.md:320; D81.
3. **A2**: A2 not applicable (no LLM judge). Judge: none: deterministic grader Separation: n/a
4. **B1**: B1 NO (related runs exist at 50%). v1.1 counts {"0.3": {"PASS": 5, "FAIL": 60}, "0.5": {"PASS": 0, "FAIL": 9}, "0.7": {"PASS": 0, "FAIL": 9}}. Keys: results/corpus-coverage.json -> "v1.1" -> "tasks" -> "build-word2vec-pipeline" -> "0.3"/"0.5"/"0.7" -> PASS/FAIL (run counts; the key is the overlap threshold).
5. **Passes**: 14/30; per arm (nonzero only) {"run1": 2, "run3": 2, "run4": 1, "arm-readfirst": 3, "exposure-all": 2, "exposure-none": 1, "arm-evidence": 3}. **Partial among 16 failed**: min 0.0, median 0.8333, max 0.8333; 0 at >=0.9, 6 at 0; mostly far.
6. **Time**: limit 20 min (data/tasks/frontier-memory/build-word2vec-pipeline/task.toml [agent] timeout_sec); agent minutes all trials median 4.7, max 7.7; failed trials median 5.3, max 7.7; failed at or over limit 0, over 90% 0, over 50% 0; median input/output tokens 321,458/13,635 (max input 751,494); exceptions none, model_unavailable 0, invalid 0.
7. **Headroom (I)**: I: the prompt names no path or interface ("callable interface and artifact layout used by prior implementations"); memory could supply the output path (/workspace/solution.py), function name/signature and the preprocessing conventions. Pipeline-audit: most gate failures wrote no /workspace/solution.py (results/pipeline-audit.md Only-for-our-setup).

### cattrs-compositional-changelog

1. **Verifier**: hidden tests plus one binary preference check on model.patch; 77 checks; strict pass = 70 F2P + 7 P2P (76 behaviour + 1 preference) all pass; preference = documented public API + runnable example + changelog entry. All-or-nothing: yes strict. Source: data/tasks/frontier-memory/cattrs-compositional-changelog/tests/preference-verifier.md; results/cattrs-oracle-check-summary.md (table, 69/70 + 7/7, "Cases / 77").
2. **Oracle**: 0 (76/77: reference misses the preference check) (measured: yes). A1 YES formal (reference 0 < 1). Not infeasible in practice: 4 of 30 trials pass, one control trial passed 77/77 (results/pipeline-audit.md). Source: results/cattrs-oracle-check-summary.md (job 303194); frontiermemory/docs/maintainers.md:76-83; results/pipeline-audit.md (Grader).
3. **A2**: A2 not applicable (no LLM judge). Judge: none: deterministic grader Separation: n/a
4. **B1**: B1 YES (no related run at 30/50/70%). v1.1 counts {"0.3": {"PASS": 0, "FAIL": 0}, "0.5": {"PASS": 0, "FAIL": 0}, "0.7": {"PASS": 0, "FAIL": 0}}. Keys: results/corpus-coverage.json -> "v1.1" -> "tasks" -> "cattrs-compositional-changelog" -> "0.3"/"0.5"/"0.7" -> PASS/FAIL (run counts; the key is the overlap threshold).
5. **Passes**: 4/30; per arm (nonzero only) {"run3": 1, "run4": 1, "exposure-none": 2}. **Partial among 26 failed**: min 0.9221, median 0.987, max 0.987; 26 at >=0.9, 0 at 0; near-miss (all failures >= 0.9).
6. **Time**: limit 90 min (data/tasks/frontier-memory/cattrs-compositional-changelog/task.toml [agent] timeout_sec); agent minutes all trials median 35.1, max 53.0; failed trials median 34.1, max 53.0; failed at or over limit 0, over 90% 0, over 50% 3; median input/output tokens 9,368,141/83,573 (max input 15,325,261); exceptions none, model_unavailable 0, invalid 0.
7. **Headroom (I)**: I: exactly the preference (public API gets docs, a runnable example, and a changelog entry), which the instruction does not state and the reference omits; functional behaviour (partial_structure) is the instruction, not memory.

### cookie-store-compositional-changelog

1. **Verifier**: hidden tests plus 4 preference gates on model.patch; 1404 checks; strict pass = 115 functional + 1285 regression cases (4 skipped excluded) + 4 preference gates all pass. All-or-nothing: yes strict. Source: results/cookie-store-oracle-check-summary.md (job 303213 table); data/tasks/frontier-memory/cookie-store-compositional-changelog/tests/preference-verifier.md.
2. **Oracle**: 0 (functional 115/115; 2 of 4 preference gates fail) (measured: yes). A1 YES formal (reference 0 < 1). Not infeasible in practice: 2 of 30 trials pass. Note the Singularity check also logged one regression error (tmp dir ownership, environment) and ended FAILED; the later Docker-guest oracle matched the maintainers list.. Source: results/cookie-store-oracle-check-summary.md; D70/D81 (match maintainers: 0); frontiermemory/docs/maintainers.md:76-83.
3. **A2**: A2 not applicable (no LLM judge). Judge: none: deterministic grader Separation: n/a
4. **B1**: B1 YES at 50 and 70 pct (none); 1 run(s) at 30 pct. v1.1 counts {"0.3": {"PASS": 0, "FAIL": 1}, "0.5": {"PASS": 0, "FAIL": 0}, "0.7": {"PASS": 0, "FAIL": 0}}. Keys: results/corpus-coverage.json -> "v1.1" -> "tasks" -> "cookie-store-compositional-changelog" -> "0.3"/"0.5"/"0.7" -> PASS/FAIL (run counts; the key is the overlap threshold).
5. **Passes**: 2/30; per arm (nonzero only) {"control": 1, "exposure-none": 1}. **Partial among 28 failed**: min 0.5772, median 0.812, max 0.9913; 4 at >=0.9, 0 at 0; mostly far. Parts keys: ['gates', 'tests'].
6. **Time**: limit 90 min (data/tasks/frontier-memory/cookie-store-compositional-changelog/task.toml [agent] timeout_sec); agent minutes all trials median 33.4, max 46.6; failed trials median 33.4, max 46.6; failed at or over limit 0, over 90% 0, over 50% 1; median input/output tokens 7,989,540/90,191 (max input 12,860,818); exceptions none, model_unavailable 0, invalid 0.
7. **Headroom (I)**: I: the preference gates (docs introduce CookieStore, copyable example, mocks not a live server in added tests, no debug artifacts) are conventions memory could carry; the functional spec is long and in the instruction.

### customer-delivery-contextual-preferences

1. **Verifier**: hidden tests plus 3 preference checks on the submitted code/patch; 191 checks; strict pass = 26 F2P + 162 P2P (incl. build gate) + 3 preference checks all pass. All-or-nothing: yes strict. Source: results/customer-delivery-oracle-check-summary.md (table); data/tasks/frontier-memory/customer-delivery-contextual-preferences/tests/preference-verifier.md.
2. **Oracle**: 1 (188/188, preference 3/3) (measured: yes). A1 NO. Source: results/customer-delivery-oracle-check-summary.md (job 303268); D81.
3. **A2**: A2 not applicable (no LLM judge). Judge: none: deterministic grader Separation: n/a
4. **B1**: B1 YES (no related run at 30/50/70%). v1.1 counts {"0.3": {"PASS": 0, "FAIL": 0}, "0.5": {"PASS": 0, "FAIL": 0}, "0.7": {"PASS": 0, "FAIL": 0}}. Keys: results/corpus-coverage.json -> "v1.1" -> "tasks" -> "customer-delivery-contextual-preferences" -> "0.3"/"0.5"/"0.7" -> PASS/FAIL (run counts; the key is the overlap threshold).
5. **Passes**: 0/30; per arm (nonzero only) none. **Partial among 30 failed**: min 0.9681, median 0.9894, max 0.9947; 30 at >=0.9, 0 at 0; near-miss (all failures >= 0.9).
6. **Time**: limit 90 min (data/tasks/frontier-memory/customer-delivery-contextual-preferences/task.toml [agent] timeout_sec); agent minutes all trials median 34.0, max 54.7; failed trials median 34.0, max 54.7; failed at or over limit 0, over 90% 0, over 50% 3; median input/output tokens 8,658,562/88,190 (max input 13,567,724); exceptions none, model_unavailable 0, invalid 0.
7. **Headroom (I)**: I: the three preferences (a runnable async-failure example, AwilixInitializationError keeps registration id and cause, monotonic timing via performance.now/hrtime) are conventions memory could supply; none is in the instruction.
8. **Never passes**: yes. Why: missing preference conventions, no source (near miss) (grade O (near miss) / I (why)). partial 0.968-0.995 in 30/30 (all >= 0.9, O) so functional work is nearly complete; strict fails on preference checks (inferred: oracle passes 188/188 + 3/3, instruction states none of them; per-check parts not in the partial file, not measured). B1 YES.

### dapt-intrusion-detection-workflow-learning

1. **Verifier**: hidden tests; 37 checks; strict pass = all pytest cases on the filled CSV pass (37 collected in the oracle check; test.sh writes reward 1 only on pytest success). All-or-nothing: yes strict. partial-credit values are multiples of 1/14, which does not match the 37 collected cases (scripts/partial_credit.py reads ctrf tests); denominator discrepancy not resolved Source: results/frontiermemory-dapt/oracle-check-summary.md:14; data/tasks/frontier-memory/dapt-intrusion-detection-workflow-learning/tests/test.sh:12-24.
2. **Oracle**: 1 (37/37) (measured: yes). A1 NO. Source: results/frontiermemory-dapt/oracle-check-summary.md:14; D70/D81.
3. **A2**: A2 not applicable (no LLM judge). Judge: none: deterministic grader Separation: n/a
4. **B1**: B1 NO (related runs exist at 50%). v1.1 counts {"0.3": {"PASS": 0, "FAIL": 35}, "0.5": {"PASS": 0, "FAIL": 35}, "0.7": {"PASS": 0, "FAIL": 35}}. Keys: results/corpus-coverage.json -> "v1.1" -> "tasks" -> "dapt-intrusion-detection-workflow-learning" -> "0.3"/"0.5"/"0.7" -> PASS/FAIL (run counts; the key is the overlap threshold).
5. **Passes**: 0/30; per arm (nonzero only) none. **Partial among 30 failed**: min 0.2143, median 0.6429, max 0.8571; 0 at >=0.9, 0 at 0; mostly far.
6. **Time**: limit 90 min (data/tasks/frontier-memory/dapt-intrusion-detection-workflow-learning/task.toml [agent] timeout_sec); agent minutes all trials median 10.6, max 43.6; failed trials median 10.6, max 43.6; failed at or over limit 0, over 90% 0, over 50% 0; median input/output tokens 709,272/29,487 (max input 5,946,648); exceptions none, model_unavailable 0, invalid 0.
7. **Headroom (I)**: I: procedure for computing the statistics from the pcap (library, bucket convention, entropy definition) could come from memory; exact numeric agreement with the test tolerances is execution. The corpus holds 35 related runs, none passing.
8. **Never passes**: yes. Why: capability (numeric computation), grader and source ruled out (grade I). Oracle passes 37/37; partial 0.21-0.86, none >= 0.9; no exceptions, median 10.6 min of 90, max 43.6; the corpus holds 35 related runs and none passes at any overlap (v1.1 0/35 at 30/50/70%), so even the source has no success to learn from. Cause not determined at task level; trajectories needed.

### enterpriseops-csm-26d1b04a

1. **Verifier**: hidden tests (4 database_state SQL checks); 4 checks; strict pass = all 4 checks pass (grade.py: reward 1.0 iff passed == len(results)). All-or-nothing: yes strict. Source: data/tasks/frontier-memory/enterpriseops-csm-26d1b04a/tests/checks.json (checks, 4 database_state); data/tasks/frontier-memory/enterpriseops-csm-26d1b04a/tests/grade.py:240.
2. **Oracle**: 0 (reference replays nothing: solution/calls.jsonl is empty) (measured: yes). A1 YES formal (reference 0 < 1) but uninformative: the reference is empty, so it says nothing about feasibility. Feasible by observation: 19 of 30 trials pass. Source: frontiermemory/docs/maintainers.md:76-83 (lines 82-83); D70/D75/D81.
3. **A2**: A2 not applicable (no LLM judge). Judge: none: deterministic grader Separation: n/a
4. **B1**: B1 NO (related runs exist at 50%). v1.1 counts {"0.3": {"PASS": 16, "FAIL": 64}, "0.5": {"PASS": 9, "FAIL": 25}, "0.7": {"PASS": 8, "FAIL": 17}}. Keys: results/corpus-coverage.json -> "v1.1" -> "tasks" -> "enterpriseops-csm-26d1b04a" -> "0.3"/"0.5"/"0.7" -> PASS/FAIL (run counts; the key is the overlap threshold).
5. **Passes**: 19/30; per arm (nonzero only) {"control": 2, "run1": 2, "run4": 2, "arm-placebo": 1, "arm-readfirst": 2, "exposure-all": 2, "exposure-none": 3, "arm-evidence": 3, "arm-blend": 2}. **Partial among 11 failed**: min 0.75, median 0.75, max 0.75; 0 at >=0.9, 0 at 0; mostly far.
6. **Time**: limit 30 min (data/tasks/frontier-memory/enterpriseops-csm-26d1b04a/task.toml [agent] timeout_sec); agent minutes all trials median 4.4, max 10.2; failed trials median 4.8, max 10.2; failed at or over limit 0, over 90% 0, over 50% 0; median input/output tokens 450,296/11,663 (max input 1,375,027); exceptions none, model_unavailable 0, invalid 0.
7. **Headroom (I)**: I: the policy is in the instruction (11 KB); memory could supply which tables/fields and the order of operations for this lifecycle; failed trials all land on exactly 3 of 4 checks, so one specific check is missed.

### enterpriseops-teams-2725d17f

1. **Verifier**: hidden tests (4 database_state SQL checks); 4 checks; strict pass = all 4 checks pass (grade.py: reward 1.0 iff passed == len(results)). All-or-nothing: yes strict. Source: data/tasks/frontier-memory/enterpriseops-teams-2725d17f/tests/checks.json (checks, 4 database_state); data/tasks/frontier-memory/enterpriseops-teams-2725d17f/tests/grade.py:240.
2. **Oracle**: 0 (reference replays nothing: solution/calls.jsonl is empty) (measured: yes). A1 YES formal (reference 0 < 1) but uninformative: the reference is empty, so it says nothing about feasibility. Feasible by observation: 2 of 30 trials pass. Source: frontiermemory/docs/maintainers.md:76-83 (lines 82-83); D70/D75/D81.
3. **A2**: A2 not applicable (no LLM judge). Judge: none: deterministic grader Separation: n/a
4. **B1**: B1 NO (related runs exist at 50%). v1.1 counts {"0.3": {"PASS": 7, "FAIL": 37}, "0.5": {"PASS": 6, "FAIL": 28}, "0.7": {"PASS": 6, "FAIL": 28}}. Keys: results/corpus-coverage.json -> "v1.1" -> "tasks" -> "enterpriseops-teams-2725d17f" -> "0.3"/"0.5"/"0.7" -> PASS/FAIL (run counts; the key is the overlap threshold).
5. **Passes**: 2/30; per arm (nonzero only) {"exposure-all": 1, "arm-evidence": 1}. **Partial among 28 failed**: min 0.75, median 0.75, max 0.75; 0 at >=0.9, 0 at 0; mostly far.
6. **Time**: limit 30 min (data/tasks/frontier-memory/enterpriseops-teams-2725d17f/task.toml [agent] timeout_sec); agent minutes all trials median 1.6, max 4.9; failed trials median 1.5, max 3.2; failed at or over limit 0, over 90% 0, over 50% 0; median input/output tokens 177,219/3,234 (max input 799,387); exceptions none, model_unavailable 0, invalid 0.
7. **Headroom (I)**: I: Microsoft Graph/table conventions and the rule that triggers the missed check; failed trials all land on exactly 3 of 4 checks. Median run is 1.6 minutes, so the agent may stop early.

## 3. Time-limit screen (A6 candidates)

No failed trial in any task reached its agent time limit (agent_started to agent_finished). The highest share of the limit used by a failed trial: awilix implicit 61%, customer delivery 61%, cattrs 59%, awilix explicit 51%, cookie store 52%, chatgpt proposal 52%, partnership 51%. So no task is a wall-clock A6 candidate on this evidence. Two caveats the per-arm analysts should keep: (a) the three AutomationBench instructions state a budget of about 50 tool-using turns, a step limit that wall time does not show; (b) agent time excludes build and verifier time. Early stops are the opposite pattern: 14 of 27 failed seat-surplus trials ran under 3 minutes (passes took 11.4 to 17.9), and Teams has a 1.6-minute median. These are leads, not assignments.

## 4. Never-pass tasks (6, not 7)

| Task | Category | Grade | Evidence |
|---|---|---|---|
| apex-eurogrid-curtailment | grader | O | Reference scores 0.8333 and all 30 trials score exactly 0.8333 (summary reward; partial-credit strict/partial); strict 1 unreachable under this verifier (A1). Judge named three ways (A2). |
| automationbench-sales-chatgpt-proposal-customization | capability or missing policy (undetermined) | I | Grader feasible (AutomationBench oracle 3/3), no exceptions, all 30 valid, partial 0.5-0.9 (median 0.7, 1 trial at 0.9); the corpus count at 30/50% (45 runs) is identical across the three AutomationBench tasks, which fits matching the shared prompt preamble rather than the task (B1 unreliable). Trajectories needed. |
| awilix-release-tier-explicit | missing preference fact, no source | O (that preference gate fails) / I (why) | partial-credit parts: preference = 0.0 in 30/30 trials (O); functional tests at full score (0.958 = 23/24 with the skip counted as not passed, same ceiling as the passing oracle) in 22/30. The oracle passes. Needed fact (version 12.1.0) is absent from the instruction; corpus holds no related run (B1). |
| awilix-release-tier-implicit | missing preference fact, no source | O / I | preference = 0.0 in 30/30 (O); full functional score in 22/30; instruction does not mention a release tier at all; oracle passes; B1 YES. |
| customer-delivery-contextual-preferences | missing preference conventions, no source (near miss) | O (near miss) / I (why) | partial 0.968-0.995 in 30/30 (all >= 0.9, O) so functional work is nearly complete; strict fails on preference checks (inferred: oracle passes 188/188 + 3/3, instruction states none of them; per-check parts not in the partial file, not measured). B1 YES. |
| dapt-intrusion-detection-workflow-learning | capability (numeric computation), grader and source ruled out | I | Oracle passes 37/37; partial 0.21-0.86, none >= 0.9; no exceptions, median 10.6 min of 90, max 43.6; the corpus holds 35 related runs and none passes at any overlap (v1.1 0/35 at 30/50/70%), so even the source has no success to learn from. Cause not determined at task level; trajectories needed. |

## 5. Oddities and contradictions found

- Seven versus six never-pass tasks (taxonomy sections 1 and the task brief versus the summary files).
- Three judges are named for APEX: file `grading_config.json` (vertex_ai/gemini-2.5-flash), CLI pin (openai/gpt-5.6-sol), and the one used (anthropic/claude-opus-5-5). Separation on wrong outputs is not measured.
- Eurogrid: reference 0.8333 and all 30 trials exactly 0.8333, so the missed criterion is identical across 31 attempts. On market share and seat surplus every failed trial is exactly 0.0, so the judge is effectively binary there.
- Awilix partial credit cannot reach 1 even for the passing oracle (tests = 23/24 with the skipped test counted as not passed), and the preference part is 0.0 in 30/30 trials. Read "partial 0.479" as "functional done, preference missed", not as a half-done solution.
- DAPT partial values are multiples of 1/14 while the oracle check collected 37 cases; denominators not reconciled.
- The AutomationBench corpus overlap counts (45 at 30% and 50% for all three tasks) are identical, which looks like shared-preamble matching; B1 for those three is unreliable. The pipeline audit itself calls the coverage "approximate".
- Cookie store oracle in the Singularity check ended FAILED on an environment error (tmp dir), while D75/D81 record a match with the maintainers in the Docker guest.
- A1 for cattrs and cookie store is formal only: the preference check, the part memory could supply, is also what the reference omits.
