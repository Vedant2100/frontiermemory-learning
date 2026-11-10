# FrontierMemory study: detailed status and decisions (engineering notes; the readable summary is README.md)

*Updated Nov 9, 2026. Target: FORGE 2027 Data & Benchmarking, due Nov 15 ([call](https://conf.researchr.org/track/forge-2027/forge-2027-data-and-benchmarking-track)). Earlier study: [pilot archive](results/pilot-v1-README.md).*

## Summary

- **The problem:** our first study used a custom memory generator, Codex, Apptainer and our own runner. Any result about memory gains could be blamed on that setup, so it can't say anything about the benchmark's real pipeline.
- **The decision:** restart the whole experiment on the official setup. Only the model differs. The first study becomes a pilot and is never pooled with the new data.
- **The paper:** an audit of FrontierMemory that traces where memory's value can be lost: corpus → generation → harness → agent → grader. It shows what a score can and can't tell you.
- **Status (Nov 9):** the preregistered main test is done (no pooled gain, +0.01 per task, p = 0.50) and the paper draft is complete (4 pages plus references; the sources are in `paper/`). The cluster is finishing the exploratory arms (none-shown running, all-shown rerun, evidence, generator; about Nov 12; cue, raw, Claude Code and recency are not run, amendment B5). The second machine is released for a quick ALFWorld memory test (below). Go/no-go on submitting is Nov 11, submission Nov 15.

## Results so far

*Updated after each set. Last update: Nov 9, 17:00: all-shown ran but is not reported (D136), none-shown running.* A trial passes only with reward 1. Per-trial data: `results/official/summary-*.jsonl`. Decisions: `results/decisions-log-detailed.md`.

### Counted sets

| Set | Memory | Status | Passed | Valid | Gave up on the model | Serving faults |
|---|---|---|---|---|---|---|
| Control | none | done Nov 5 03:18 (14.4 h) | 6/45 | 45/45 | 0 | 0 (D105) |
| Run 1 | generation 1: 13 files, 62 KB | done Nov 5 18:37 (15.3 h with generation) | 7/45 | 45/45 | 0 | 0 (D107: 1 model tool-call parse 500, recovered on retry) |
| Run 2 | generation 2: **timed out at 6 h, no memory** (D113) | reported, trials not run (prereg) | – | – | – | – |
| Run 3 | generation 3: 6 files, 40 KB | done Nov 6 14:27 (13.7 h) | 4/45 | 45/45 | 0 | 0 |
| Run 4 (replaces run 2, A4) | generation 4: 7 files, 38 KB (21 min) | done Nov 7 22:31 (15.9 h with generation) | 8/45 | 45/45 | 0 | 0 |
| Placebo (exploratory arm, fast-tracked) | run 1's files, same file count and byte sizes, text replaced by public-domain prose | done Nov 7 06:27 (15.8 h) | 4/45 | 45/45 | 0 | 0 outside the D122 Ollama hang; its one overlapping trial set aside and rerun (B3, D124) |
| Read-first (exploratory arm) | run 1's, plus a nudge to read it first | done Nov 8 12:16 (13.5 h; checks fixed first, D125–D129) | 8/45 | 45/45 | 0 | 0 (16 of 16 closes at an agent's end); one trial with no reward (environment command timed out before the agent started) set aside and rerun |
| All shown (exploratory) | run 1's, every file in the prompt | done Nov 10 12:53 after the D136/B5 rerun of 10 stalled trials | 7/45 | 45/45 | clean after rerun | ok (D139) |
| None shown (exploratory) | run 1's, no memory shown at start, files on disk | done Nov 10 02:50 (15.6 h) | 9/45 | 45/45 | 0 | ok (D138) |
| Next (arms amendment B5, Nov 9) | | all-shown's 10 stalled trials rerun, then evidence, then generator; about Nov 12. Cue, raw, Claude Code (K0, KM) and recency a/b not run | | | | |

**Second machine (separate study, its own preregistration; numbers never compared with the above):** Codex without memory 6/45, with the same run 1 memory 7/45 (45/45 valid in each). One exploratory test on DAPT put the memory into the task instruction (rewritten once by the same local model): 0/3 strict in all three conditions, hidden tests passed 52% without memory, 74% with it, 76% blended. Claude Code's gate failed twice because model calls were still in flight when trials hit the 90-minute agent limit (start plus duration of each close lands 12 to 40 s after the timeout); K0, KM and recency a/b are not run anywhere (amendment B5). The machine now runs an exploratory ALFWorld memory test.

**Exposure arms (exploratory, D139):** none shown 9/45, all shown 7/45, read-first 8/45, run 1 7/45, no memory 6/45: strict passes do not follow how much memory is shown. Paired per-task differences are all within noise: all shown vs run 1 0.00 (95% CI −0.09 to +0.09, p = 0.69); none shown vs run 1 +0.04 (−0.08 to +0.19, p = 0.38); all shown vs no memory +0.02 (−0.12 to +0.17, p = 0.50). Hidden tests passed (mean over 45): no memory 58%, run 1 65%, none shown 61%, read-first 65%, all shown 69%; all shown vs no memory +0.11 (−0.01 to +0.26, one-sided p = 0.07), vs run 1 +0.04 (p = 0.18): the largest hidden-test difference of any arm, still inside the noise at 15 tasks. Word2Vec hidden tests passed: no memory 0%, run 1 83/100/100%, none shown 83/83/100%, all shown 83/100/100%: the Word2Vec gain does not depend on the memory being shown at the start, since the agent finds it when it is only on disk.

**Placebo (exploratory; the arms preregistration's test):** 4/45, vs run 1 (same file layout, real content) −0.07 per task (95% CI −0.19 to +0.06), 1 task up, 3 down, p = 0.94; vs no memory −0.04, p = 0.89. The Word2Vec gain does not appear with placebo text (0/3, vs 5 of 9 across the three real-memory runs): consistent with the content, not the presence of files, mattering there, but one task with 3 attempts each.

**Primary result (preregistered, runs 1, 3 and 4 pooled vs no memory):** per-task pass rate +0.01 (95% CI −0.12 to +0.14), 4 tasks up, 4 down, one-sided p = 0.50. Pooled: 19 of 135 with memory vs 6 of 45 without. Sensitivity: without the 4 tasks whose reference solution fails, +0.04, p = 0.34; without run 4 (the replacement run), −0.01, p = 0.63. Not evidence of a gain, and with 15 tasks not evidence of no effect either. Shortfall stated: 3 of 4 memory runs have trials (run 2's generation timed out). The one consistent change is Word2Vec: 0/3 without memory, 2, 2 and 1 of 3 in the three memory runs.

**Read-first (exploratory):** the nudge nearly doubled how often the agent opened its memory, 15 of 45 trials (run 1) to 27 of 45, and opened it sooner (median 2 tool calls before the first open, against 5), mostly on tasks that never opened it before (awilix 0/3 to 2/3, cookie store 0/3 to 2/3, DAPT 1/3 to 3/3). The score did not move: 8/45 vs 7/45 strict passes (per task +0.02 vs run 1, p = 0.50), hidden tests 65.4% vs 65.2%. Word2Vec already opened the memory 3 of 3 times in run 1, with no nudge. So in this setup delivery is not the bottleneck; what the memory says is (`scripts/memory_access.py`, D132).

**Hidden tests passed (preregistered secondary, `scripts/partial_credit.py`, D131):** the share of each verifier's hidden tests (or rubric checks) an attempt passes, by the verifier's own partial-credit field where it has one, else its printed test counts. Means over 45 trials: no memory 58%, run 1 65%, run 3 59%, run 4 67%, placebo 60%. Runs 1, 3, 4 vs no memory: +0.06 per task (95% CI −0.07 to +0.20, one-sided p = 0.25, 7 tasks up, 7 down), the same picture as strict passes. Word2Vec: 0% of hidden tests without memory and with placebo (all 6 attempts failed before any test ran), 72–94% with real memory. AutoBench partnership drops from 51% to 17–25% in every memory arm, placebo included. Consistency check: a trial's partial credit is 1 exactly when its strict reward is 1, on all 225 trials.

### Per task (3 attempts each)

| Task | Control | Run 1 | Run 3 | Run 4 | Placebo | Read-first |
|---|---|---|---|---|---|---|
| build-word2vec-pipeline | 0/3 | **2/3** | **2/3** | **1/3** | 0/3 | **3/3** |
| apex-brightpath-market-share | 0/3 | 1/3 | 0/3 | 2/3 | 1/3 | 0/3 |
| cattrs compositional changelog (reference solution scores 0) | 0/3 | 0/3 | 1/3 | 1/3 | 0/3 | 0/3 |
| automationbench marketing content gap analysis | 2/3 | 2/3 | 1/3 | 1/3 | 1/3 | 3/3 |
| enterpriseops CSM | 2/3 | 2/3 | 0/3 | 2/3 | 1/3 | 2/3 |
| automationbench sales partnership contract | 1/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| cookie-store compositional changelog | 1/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| apex-brightpath-seat-surplus | 0/3 | 0/3 | 0/3 | 1/3 | 1/3 | 0/3 |
| the other 7 (Eurogrid scores 0.83 every attempt, its maximum reachable reward per the maintainers) | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |

### Audit findings: where the official pipeline loses value

| # | Finding | Effect | Basis |
|---|---|---|---|
| 1 | Harbor's egress proxy cuts any response whose first byte takes over 15 s. Cloud models answer sooner, so official runs never hit it; a local or slow model does | First control: 420 cut requests, 3 of 41 trials given up and scored as failures. That control was discarded (D93–D94). Fixed with a relay that starts the response at once (protocol v4) | M |
| 2 | Hermes at effort max cancels any call after 300 s, but the cancel doesn't reach the model server, so retries queue behind abandoned calls. After 5 cancels it gives up (`model_unavailable`) | Gate 1: customer delivery and awilix both gave up. Short-task gates missed it twice; only a gate with the longest task caught it (D100–D101). Fixed with Hermes's own timeout settings, disclosed as a deviation (amendment A3) | M |
| 3 | Hermes's post-answer memory review starts as the agent finishes and is cut when the container stops | Every trial loses that review. It doesn't affect scores, but the official pipeline drops part of the harness's own memory step (D99, D104) | M |
| 4 | Harnesses show different shares of the same memory at the start | Of the entry file: Codex about 21%, Claude Code about 48%, Hermes 100% ([survey](results/harness-exposure-survey.md)). Of the whole memory, Hermes shows much less (finding 6). The exposure arms test the effect | M (simulated) |
| 5 | No released task needs newer corpus evidence to win | Recency can't be tested on the released corpus ([check](results/recency-check.md), D97) | M |
| 6 | Hermes shows only MEMORY.md and its skill index at start: 1 of 13 memory files in run 1. The rest must be opened by the agent | Measured from saved system prompts (D106); the survey's "Hermes 100%" refers to MEMORY.md only | M |
| 7 | A malformed tool call from the model surfaces as an Ollama HTTP 500 | Once in about 4,100 calls; Hermes's identical retry recovered it (D107) | M |

## The new setup

Letta Dream and Letta's Letta Code loader aren't public, so we can't run the default leaderboard setup. We use **Hermes**, a published leaderboard row that the public repo provides as both generator and task agent. Full checklist: [protocol v4](results/protocol-v4-official.md). Analysis plan: [preregistration v2](results/preregistration-v2.md) (draft).

| Item | Pilot | Restart |
|---|---|---|
| Generator | Custom scripted pipeline | Hermes `/learn`, pinned commit |
| Task agent | Codex | Hermes |
| Runtime | Apptainer | Docker (`-e docker`) |
| Runner | Our own | `frontier-memory` commands |
| Tasks | 7 | All 15 |
| Trials | 5 per arm, one memory | 3 runs × 3 attempts (135), plus 45 no-memory |
| Corpus | v1.0 | v1.1, as on the leaderboard |
| Effort | Medium | Highest, as on the leaderboard |
| **Model** | **Qwen3.8-27B, local** | **Qwen3.8-27B, local (the one allowed difference)** |

**Docker without an admin:** the cluster has no Docker, but `/dev/kvm` works inside our Slurm jobs. So we run real Docker in our own VM, with the model on the host GPU. KVM access is tested; booting the VM and running Docker aren't yet. If it fails, the fallback is Modal, at about $400–600. Modal lists academic credits of up to $10k.

## Timeline

Dates after Nov 4 are estimates.

| When | What |
|---|---|
| Nov 2–3 | **Done:** records and docs. VM and Docker built, reproducibly, from scripts |
| Nov 3 | **Done:** network probe; reference solutions on all 15 tasks match the maintainers; full-setting generation and Word2Vec gate |
| Nov 3 | **Done:** smoke test; preregistration locked |
| Nov 4 | **Done:** first control discarded (proxy cut, D93); gate 1 failed (Hermes give-ups, D100); gate 2 passed (D102) |
| Nov 4–5 | **Done:** counted control (D105) |
| Nov 5 | **Done:** run 1 (D107) |
| Nov 5–8 | **Done:** run 2 (timed out), run 3, run 4, placebo, read-first |
| Nov 8–9 | All-shown: ran, 10 of 45 trials hit model-server stalls (D136) |
| Nov 9–12 | None-shown (running), all-shown rerun of the 10 trials, evidence, generator (B5) |
| Nov 5–9 | **Done:** audit of the real pipeline; paper draft complete and reviewed; anonymized artifact built (`scripts/build_artifact.sh`) |
| **Nov 11** | **Go/no-go:** submit with the runs finished, stating the shortfall, or move to EASE (Jan 22) |
| Nov 12–14 | Final read-through of the paper, re-run `scripts/build_artifact.sh`, update numbers if the rerun changes any |
| Nov 15 | Submit to FORGE |
| After FORGE | Better generator, then EASE |

**If Qwen can't drive Hermes in the smoke test,** we stop and decide. The fallback is the Codex route, which is public code but not a published leaderboard row.

## What's next

- **ALFWorld memory test (second machine, exploratory, separate from this study):** no memory, static tips, raw past trajectories, a summarizing writer and a prompted Letta-style writer, with memory built on one split, frozen and tested on 134 unseen tasks. Bar fixed before running: at least +15 points over no memory and +10 over the static tips, in at least 4 of 6 task types. Static tips guard against memory merely teaching command syntax in templated tasks.
- **After FORGE:** (1) a hand-written note per task, built only from facts in the corpus, to measure each task's headroom and the generator's extraction efficiency; (2) leave-one-file-out and per-claim attribution on Word2Vec; (3) the leaderboard-reliability analysis as a short methods note; (4) tasks built so that memory is needed, goes stale or is wrong.

## Answers to our questions

Basis: **S** = read in official docs or code, **M** = measured by us, **I** = our inference.

| Question | Answer | Basis |
|---|---|---|
| Is our old generator Letta Dream? | No. Dream is [the official default](https://frontiermemory.com/blog/v1/), and its code isn't in the public repo. It isn't required: [the rules](https://github.com/letta-ai/frontiermemory/blob/main/docs/rules.md) allow any generator | S |
| Does the benchmark report latency? | No. The [leaderboard](https://frontiermemory.com/) shows score and task cost only, with no latency, tokens, memory size, per-task results or no-memory row | S |
| Would a cache help? | Unlikely. Memory is local files, and model turns take tens of seconds in our runs. Memory saves exploration instead: Word2Vec fell from 9.0 to 3.1 min in the pilot | M |
| Does the score test recency? | No. [The release is offline](https://frontiermemory.com/blog/v1/), with online updates planned. Whether any task needs newer evidence over older is unchecked | S |
| Do harnesses size memory to the context window? | Not the index. Codex caps it at 2,500 tokens, and [Claude Code](https://code.claude.com/docs/en/memory) at 200 lines or 25 KB. That's 3.8% of a 65k window and 0.25% of a 1M window | S |
| Does the memory shown differ by harness? | Yes. For one memory: Codex 21%, Claude Code 48%, Agents SDK and Hermes 100%, Letta Code unknown. [Simulated from each rule](results/harness-exposure-survey.md), with the effect on outcomes untested | M |
| Would Claude's limit help Codex? | Not on the pilot's failures: DAPT's index line was outside both windows, and Word2Vec already passed. Hermes loads the whole file, so this matters less now | M |
| Is System 1/2 an established memory idea? | The term mostly means fast vs deliberate processing ([D-Mem](https://arxiv.org/abs/2603.18631), [Jev-Mem](https://arxiv.org/abs/2609.23986)). Always-on vs situational is closer to our shown vs sought, and [Delivery, Not Storage](https://arxiv.org/abs/2607.20972) adds cue-triggered injection | S |
| Is categorized memory new? | No. The official instruction already asks for semantic memory and procedural skills, and [the blog](https://frontiermemory.com/blog/v1/) uses task, user and environment categories | S |
| Is the corpus even across tasks? | No, at least in v1.0: from 0 related runs (cattrs) to about 31 (DAPT-like), by rough [keyword counts](results/preference-feedback-trace.md). [v1.1 aimed to balance sources](https://frontiermemory.com/changelog); we'll recount | M |
| Are the graders sound? | Questionable. [Maintainers report](https://github.com/letta-ai/frontiermemory/blob/main/docs/maintainers.md) the reference solution scores 0 on 4 of 15 tasks, and [the blog](https://frontiermemory.com/blog/v1/) says 53% of the sourced tasks it kept had broken verifiers, since repaired | S |
| How precise is the leaderboard? | All 15 published scores are multiples of 1/45, which fits 3 runs × 15 tasks. On that grid, rank 1 and 2 differ by one trial. No per-task data is published to test gaps | I |

## What the paper will claim

**True of the benchmark for any model:** corpus coverage, grader limits, unreported baselines and per-task results, fixed memory caps.

**True only of our setup:** gains from memory, memory quality, agent failures such as early stops.

We won't claim leaderboard scores are wrong, since we don't run their models.

Closest work: [VibeMemBench](https://arxiv.org/abs/2609.23570), [MERIT](https://arxiv.org/abs/2609.05441). We read abstracts only so far, and must read these in full before citing.

## After the baseline

- **Better generator:** designed from failures we observe in official generation, plus scoped or categorized memory and cue-triggered delivery. It goes through the official custom-harness path, with its own preregistration. It won't be tuned on target task results. Probably after FORGE.
- **Leaderboard:** a submission needs a harness PR and 135 trials on Opus 5.5 or GPT-6 Sol, about $460 plus judge costs. Our budget is zero, so it needs funding or Letta's help.
- **Next paper idea:** stale memory in coding agents. [STALE](https://arxiv.org/abs/2605.06527) and [Memory Trust Gap](https://arxiv.org/abs/2609.01852) test it outside coding.

## Needed

1. **OpenAI key (optional, later):** 3 APEX tasks use a documented OpenAI judge. For now they use a Claude judge, a disclosed deviation that reproduced the reference scores. With a valid OpenAI key, we regrade the saved trials without rerunning the agent, and those results become primary.
3. **Optional insurance:** apply for [Modal academic credits](https://modal.com/pricing) in case the VM route fails.
4. **Cluster check:** consider mentioning the VM to the admin. It stays within our allocation, and we haven't seen a policy on it.
