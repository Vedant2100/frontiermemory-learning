# Confirmatory matrix v1: interim results (updated 2026-10-31, 4/7 tasks)

Preregistration: `results/preregistration-v1.md` (tags `prereg-v1`, `-a4`, `-a5`). Arms: A0 (no memory), R25, M3; k=5 per arm; Latin order. Four of seven tasks are complete. **Interim results; no tests run yet** (the Holm-corrected analysis comes after all seven tasks finish).

## Results

| Task (job) | A0 strict | R25 strict | M3 strict | A0 cases (mean) | R25 cases (mean) | M3 cases (mean) |
|---|---|---|---|---|---|---|
| build-word2vec-pipeline (303281) | 0/5 | **5/5** | **5/5** | 0/6 | 6/6 | 6/6 |
| dapt-intrusion-detection-workflow-learning (303282) | 0/5 | 1/5 | 0/5 | 26.4/37 | 31.4/37 | 20.0/37 |
| awilix-release-tier-implicit (303363) | 0/5 | 0/5 | 0/5 | 138.0/184 (LB 135.0) | 174.8/184 (LB 169.0) | 169.2/184 (LB 165.0) |
| awilix-release-tier-explicit (303383) | 0/5 | 0/5 | 0/5 | 170.2/184 (LB 163.2) | 138.0/184 (LB 131.6) | 133.6/184 (LB 130.0) |

- Word2Vec: all A0 failures are `CONTRACT_COLLECTION_ERROR`, meaning the output does not meet the task's artifact contract.
- DAPT M3 per trial: 0 (NO_ARTIFACT), 31, 30, 21, 18. R25: 37, 32, 32, 24, 32. A0: 30, 21, 27, 24, 30.
- awilix-implicit per trial (cases passed, A5 lower bound in brackets where the agent added tests):
  - A0: 184, 161, 184 [169], 0 (NO_ARTIFACT: empty patch), 161.
  - R25: 161, 184, 184 [171], 161, 184 [168].
  - M3: 161, 184 [163], 161, 179, 161.
  - 161/184 means the base suite passes but the functional suite does not compile or collect.
  - Functional suite fully passing: A0 2/5, R25 3/5, M3 0/5. The user-preference check failed in all 15 trials, so strict pass is 0/15. Six trials hit the 90-min timeout (A0 3, R25 1, M3 2).
- awilix-explicit per trial (cases passed, A5 lower bound in brackets):
  - A0: 161, 184 [165], 161, 184 [168], 161.
  - R25: 184 [167], 0 (agent patch breaks the TypeScript build), 184 [169], 161, 161.
  - M3: 184 [166], 162, 161, 0 (build broken), 161.
  - Functional suite fully passing: A0 2/5, R25 1/5, M3 1/5. Preference check failed in all 15; strict 0/15. Eight trials hit the timeout (A0 1, R25 2, M3 4).
  - The two awilix tiers point in opposite directions on cases (memory ahead on implicit, behind on explicit). Each gap is driven by single 0-scoring trials.
- All 60 trials are valid. Each trial's arm label matches its seeded memory digest. R25's injected window matches `scripts/memory_exposure.py` ("match"). On awilix-implicit, all 717 logged requests that carry a memory summary match exactly one frozen memory window (R25 355, M3 362); on awilix-explicit, all 767 do (R25 466, M3 301).

## Prediction from A4: falsified

A4 predicted that M3 would not beat A0 on Word2Vec by more than 1 of 5 trials. The result was 5/5 against 0/5. A4's premise, that agents never open memory files, came from 9 exploratory DAPT and cattrs trials and did not generalize.

## How the memory was used

How often agents opened memory files themselves (grep of `MEMORY.md`, or `cat` of topic files):

| Task | R25 trials that searched or opened memory | M3 trials that did |
|---|---|---|
| Word2Vec | 5/5 (opened a Word2Vec topic) | 5/5 (grepped `MEMORY.md` for "word2vec", then opened topics) |
| DAPT | 4/5 (opened a pcap-statistics topic) | 1/5 |
| awilix-implicit | 1/5 | 2/5 |
| awilix-explicit | 0/5 | 0/5 |

On Word2Vec, the M3 agents found Word2Vec topics by searching the full index in the file, although those topics were not in the injected window. Two paths are visible:
1. the injected window, which is always seen;
2. agent-initiated search, which happens when the task cues it.

On DAPT, the R25 agents opened the topic more often and scored higher than the M3 agents. This is descriptive; there is no causal claim at n=5.
