# FrontierMemory audit: final results (closed Nov 12, 2026)

All cluster experiments are finished and the cluster job has been released. Nothing is running. Numbers below are from `results/official/` and the decision log (`results/decisions-log-detailed.md`, D1 to D145).

## The preregistered question
Does the official FrontierMemory setup (Hermes `/learn` memory, local Qwen model) beat no memory over 15 tasks?
No measurable gain: **+0.01 per task** (95% interval −0.12 to +0.14), one-sided exact paired sign-flip **p = 0.50**; 19/135 trials passed with memory against 6/45 without. Hidden tests, secondary: +0.06 (p = 0.25). A null over 15 tasks is not proof of no effect; the interval excludes mean gains above 0.14.

The one task memory helps is Word2Vec (0% of hidden tests without memory, 72–94% with it, 0% with a placebo of the same shape).

## Exploratory arms (strict passes out of 45; hidden tests passed)
| Arm | Strict | Hidden tests |
|---|---|---|
| No memory (control) | 6 | 58% |
| Run 1 memory | 7 | about 65% |
| Read-first | 8 | 65% |
| All shown (clean rerun) | 7 | 69% |
| None shown | 9 | 61% |
| Evidence (raw past runs as files) | 9 | 67% |
| Blend (memory worked into the task text, 14 tasks) | 3 | 63% |
| Placebo (unrelated text, same files) | 4 | 60% |
| Generator (better memory writer) | not run: generation hit the 6-hour limit twice, no memory exported | |

None beats run 1 by the bar set before each arm ran. Blend misses it on both halves (−0.02 per task against run 1 on hidden tests, p = 0.86; strict up on 0 tasks, down on 2). Blend, like every arm except the main test, is exploratory and is not in the paper.

## Not run
Cue, raw corpus, scoped and categorized memory (degenerate or unusable input, amendments B4 and B5), and the Claude Code and recency tests on the second machine (the Claude Code gate failed twice on model-call timing). The second machine's Codex pair (6/45 without memory, 7/45 with it) is its own study and is never compared with the cluster's numbers.

## Other findings
- Leaderboard: the top five of 12 rows are too close to call (33, 33, 32, 32, 31 of 45); under a binomial model a rerun puts the same entry first about 26% of the time.
- Reading the memory is not the bottleneck: a nudge to read it doubled opens (15 → 27 of 45 trials) and moved passes 7 → 8.
- The model server can stall (15–30 minutes with the model idle); 10 of 45 all-shown trials timed out and were rerun under a rule written beforehand.

## Deliverables
Paper (4 pages plus references, anonymous), artifact (129 files) and plan archive are in `~/fm-submission/`; rebuild the artifact with `scripts/build_artifact.sh <dir>` before submission (deadline Nov 16, 3:59 AM Pacific). The plan archive does not prove the plan predates the results.
