# Scope leakage (interim, descriptive): 4 of 7 tasks

Status: interim. Four of the seven candidate tasks have completed jobs, so these counts are not the full analysis. Descriptive only, with no inferential claims.

Method: same-family versus other-family is a token overlap between the topic slug and the task name, per prereg v1 "Scope-leakage analysis" and Amendment A4 item 3. Visible-window entries come from the first and last 5000 characters of MEMORY.md. Opened files are read commands on existing `topics/<slug>.md` files. Harm is cases_lb below the A0 task mean (Amendment A5). Script: `scripts/scope_leakage.py`.

Counts per task and arm. "vis" is visible-window entries (same/other). "opened" is the mean number of topic files opened (same/other). "harm" is the number of trials with cases_lb below the A0 mean, followed by how many of those opened an other-family topic. "non-harm" is the same for the remaining trials.

| Task | Arm | n | consulted | vis same/other | opened same/other | harm (other-opened) | non-harm (other-opened) | mean cases_lb | mean strict |
|---|---|---|---|---|---|---|---|---|---|
| build-word2vec-pipeline | A0 | 5 | 0 | 0/0 | 0/0 | n/a | n/a | 0.0 | 0.0 |
| build-word2vec-pipeline | R25 | 5 | 5 | 3/62 | 3.0/1.0 | 0 (vacuous, see note) | 5 (5) | 6.0 | 1.0 |
| build-word2vec-pipeline | M3 | 5 | 5 | 0/83 | 4.0/0.6 | 0 (vacuous) | 5 (2) | 6.0 | 1.0 |
| dapt-intrusion-detection-workflow-learning | A0 | 5 | 0 | 0/0 | 0/0 | n/a | n/a | 26.4 | 0.0 |
| dapt-intrusion-detection-workflow-learning | R25 | 5 | 4 | 1/64 | 0.0/0.8 | 1 (0) | 4 (4) | 31.4 | 0.2 |
| dapt-intrusion-detection-workflow-learning | M3 | 5 | 1 | 2/81 | 0.0/0.0 | 3 (0) | 2 (0) | 20.0 | 0.0 |
| awilix-release-tier-implicit | A0 | 5 | 0 | 0/0 | 0/0 | n/a | n/a | 135.0 | 0.0 |
| awilix-release-tier-implicit | R25 | 5 | 1 | 0/65 | 0.2/0.0 | 0 (0) | 5 (0) | 169.0 | 0.0 |
| awilix-release-tier-implicit | M3 | 5 | 2 | 0/83 | 0.4/0.0 | 0 (0) | 5 (0) | 165.0 | 0.0 |
| awilix-release-tier-explicit | A0 | 5 | 0 | 0/0 | 0/0 | n/a | n/a | 163.2 | 0.0 |
| awilix-release-tier-explicit | R25 | 5 | 0 | 0/65 | 0/0 | 3 (0) | 2 (0) | 131.6 | 0.0 |
| awilix-release-tier-explicit | M3 | 5 | 0 | 0/83 | 0/0 | 4 (0) | 1 (0) | 130.0 | 0.0 |

Notes on the table:
- Each job has 15 trials, 5 per arm (A0, R25, M3). The governance arms G and GR are not in these jobs. This matches the dropped-arm decision in Amendment A3, so k is 5 per arm rather than the k=3 written in section 3.
- For build-word2vec-pipeline, the A0 mean cases_lb is 0 (floored), so no memory trial can fall below it. For all four tasks the A0 mean strict reward is 0.0, so the strict flag cannot fire. Both harm flags are uninformative for these tasks.
- No trials were invalid, and every trial had an events file.

Observations (descriptive, interim):
- Across the three tasks where the cases_lb flag can fire, 11 of 30 memory trials were harmful. None of those 11 opened an other-family topic. Four of the 19 non-harmful memory trials did (all on DAPT with R25).
- Other-family topics were opened often on word2vec and DAPT R25, and almost never on the awilix tasks. On awilix, only 1 slug in each memory directory contains the word "awilix", so almost no same-family entries exist to open.
- On word2vec, M3 showed no same-family entries in its visible window, yet agents opened about 4 same-family topic files per trial. Four of five M3 trials searched MEMORY.md directly, so they reached topics outside the window that way.
- The same-family token rule is an upper bound. Generic task-name words such as "pipeline", "learning" and "workflow" are not stop words (per A4 item 3).
- With 5 trials per arm per task and 4 tasks, these counts can only describe, not test. The remaining tasks may change the picture.
