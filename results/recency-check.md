# Recency check: does any task need newer corpus evidence over older? (2026-11-04)

**Question.** In corpus v1.1, does any of the 15 tasks depend on newer evidence winning over older evidence? That would mean the corpus holds superseded information, such as versions, APIs, conventions or preferences that changed over time, where using the older item fails the task.

**Method.**
- **Relevant runs:** script `scripts/recency_check.py`, output `results/recency-check.json`, holding counts, run ids, timestamps and verdicts only. A run is relevant if its first user message holds at least 30% of the task instruction's distinctive words, the same rule as `scripts/corpus_coverage.py`, or if its opening names the task's repository or family.
- **Ordering:** runs are ordered by their recorded `timestamp` fields (703 of 750 runs have one, and no run spans more than one day).
- **Mechanical check:** every package pinned in the task's own build and test files (Dockerfile, requirements, `test.sh`) is checked for different versions across relevant runs. Corpus version values are compared but not written out.
- **Timing:** we compare when passing and failing runs happened.

Basis: **S** read in source, **M** measured, **I** our inference.

| Task | Relevant runs (timed) | Days | PASS / FAIL | Version conflict with a task pin | Later runs pass more? | Answer |
|---|---|---|---|---|---|---|
| apex-brightpath-market-share | 19 (19) | 5, Sep 16 – Oct 13 | 18 / 1 | none; task pins no packages (S, M) | no: passes on every day (M) | **No** |
| apex-brightpath-seat-surplus | 19 (19) | 5, Sep 16 – Oct 13 | 17 / 2 | none; no pins (S, M) | no (M) | **No** |
| apex-eurogrid-curtailment | 3 (3) | 1, Oct 13 | 2 / 1 | none; no pins (S, M) | single day (M) | **No** |
| automationbench, marketing | 45 (24) | 1, Oct 6 | 3 / 42 | none of 3 pins (S, M) | single day (M) | **No** |
| automationbench, proposal | 45 (24) | 1, Oct 6 | 3 / 42 | none of 3 pins (S, M) | single day (M) | **No** |
| automationbench, partnership | 45 (24) | 1, Oct 6 | 3 / 42 | none of 3 pins (S, M) | single day (M) | **No** |
| awilix-release-tier-explicit | 0 | – | – | – | – | **Unclear:** no matched runs |
| awilix-release-tier-implicit | 0 | – | – | – | – | **Unclear:** no matched runs |
| build-word2vec-pipeline | 66 (66) | 4, Jun 25 – 28 | 6 / 60 | none of 7 pins (S, M) | no: per-day passes 1/5, 4/32, 1/28, 0/1 (M) | **No** |
| cattrs-compositional-changelog | 0 | – | – | – | – | **Unclear:** no matched runs |
| cookie-store-compositional-changelog | 1 (1) | 1, Sep 29 | 0 / 1 | none of 10 pins (S, M) | single run (M) | **Unclear:** one run |
| customer-delivery-contextual-preferences | 0 | – | – | – | – | **Unclear:** no matched runs |
| dapt-intrusion-detection-workflow-learning | 35 (9) | 2, Jan 29 – Feb 7 | 0 / 35 | none of 5 pins (S, M) | no passes at all (M) | **No** |
| enterpriseops-csm | 80 (80) | 4, Sep 29 – Oct 16 | 16 / 64 | none; 1 pin (S, M) | no: the earliest day has the most passes, 11/37, then 0/17, 4/17, 1/9 (M) | **No** |
| enterpriseops-teams | 44 (44) | 3, Sep 29 – Oct 16 | 7 / 37 | none; 1 pin (S, M) | no: 6/18, 0/17, 1/9 (M) | **No** |

**Limits.**
- **What the check can see:** it only detects superseded package versions. A changed API, convention or user preference written in prose would need reading the runs, which we didn't do, to keep corpus text out of the study records. So "No" means "no measurable sign" (I).
- **Unmatched tasks:** the 5 "unclear" tasks have no runs matched by prompt or opening. Same-repository runs with different prompts would be missed; an earlier keyword trace on v1.0 found a few for awilix and customer delivery (`results/preference-feedback-trace.md`).
- **Short time spans:** within each task, relevant runs span 1–5 days, and 9 of 15 tasks lie within a week or less. So there is little time over which information could change (M).
- **Untimed runs:** 21 of 45 AutomationBench runs and 26 of 35 DAPT runs have no timestamp, so their order is unknown (M).

**For the paper (audit section).** We found no sign that any task needs newer corpus evidence to win over older evidence. No package pinned by a task appears with different versions across its relevant runs. Within each task those runs span at most a few weeks, often a single day, and passing runs aren't concentrated late: for EnterpriseOps the earliest day has the most. Recency handling is therefore not tested by this benchmark's score, which is consistent with its offline design. The check is mechanical: it can't see changed conventions or preferences written in prose, and 5 tasks have no matched runs at all, so for those the question can't be answered from the corpus.
