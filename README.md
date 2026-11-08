# FrontierMemory study: plan of action

*Updated Nov 5, 2026. Target: FORGE 2027 Data & Benchmarking, due Nov 15 ([call](https://conf.researchr.org/track/forge-2027/forge-2027-data-and-benchmarking-track)). Earlier study: [pilot archive](results/pilot-v1-README.md).*

## Summary

- **The problem:** our first study used a custom memory generator, Codex, Apptainer and our own runner. Any result about memory gains could be blamed on that setup, so it can't say anything about the benchmark's real pipeline.
- **The decision:** restart the whole experiment on the official setup. Only the model differs. The first study becomes a pilot and is never pooled with the new data.
- **The paper:** an audit of FrontierMemory that traces where memory's value can be lost: corpus → generation → harness → agent → grader. It shows what a score can and can't tell you.
- **Biggest risk:** time. The full run may take 7.5–12 days on one GPU server, which puts Nov 15 at risk. The decision point is Nov 11.

## Results so far

*Updated after each set. Last update: Nov 7, 22:45, after run 4: the preregistered test is complete.* A trial passes only with reward 1. Per-trial data: `results/official/summary-*.jsonl`. Decisions: `results/decisions-log-detailed.md`.

### Counted sets

| Set | Memory | Status | Passed | Valid | Gave up on the model | Serving faults |
|---|---|---|---|---|---|---|
| Control | none | done Nov 5 03:18 (14.4 h) | 6/45 | 45/45 | 0 | 0 (D105) |
| Run 1 | generation 1: 13 files, 62 KB | done Nov 5 18:37 (15.3 h with generation) | 7/45 | 45/45 | 0 | 0 (D107: 1 model tool-call parse 500, recovered on retry) |
| Run 2 | generation 2: **timed out at 6 h, no memory** (D113) | reported, trials not run (prereg) | – | – | – | – |
| Run 3 | generation 3: 6 files, 40 KB | done Nov 6 14:27 (13.7 h) | 4/45 | 45/45 | 0 | 0 |
| Run 4 (replaces run 2, A4) | generation 4: 7 files, 38 KB (21 min) | done Nov 7 22:31 (15.9 h with generation) | 8/45 | 45/45 | 0 | 0 |
| Placebo (exploratory arm, fast-tracked) | run 1's files, same file count and byte sizes, text replaced by public-domain prose | done Nov 7 06:27 (15.8 h) | 4/45 | 45/45 | 0 | 0 outside the D122 Ollama hang; its one overlapping trial set aside and rerun (B3, D124) |
| Read-first (exploratory arm) | run 1's, plus a nudge to read it first | e2e passed Nov 7 22:39 (checks fixed, D125–D129); 45 trials running, about Nov 8 evening | | | | |
| Exposure all, then none (exploratory) | run 1's | all after read-first (A7), about Nov 9; none in the arms order (A5) | | | | |

**Placebo (exploratory; the arms preregistration's test):** 4/45, vs run 1 (same file layout, real content) −0.07 per task (95% CI −0.19 to +0.06), 1 task up, 3 down, p = 0.94; vs no memory −0.04, p = 0.89. The Word2Vec gain does not appear with placebo text (0/3, vs 5 of 9 across the three real-memory runs): consistent with the content, not the presence of files, mattering there, but one task with 3 attempts each.

**Primary result (preregistered, runs 1, 3 and 4 pooled vs no memory):** per-task pass rate +0.01 (95% CI −0.12 to +0.14), 4 tasks up, 4 down, one-sided p = 0.50. Pooled: 19 of 135 with memory vs 6 of 45 without. Sensitivity: without the 4 tasks whose reference solution fails, +0.04, p = 0.34; without run 4 (the replacement run), −0.01, p = 0.63. Not evidence of a gain, and with 15 tasks not evidence of no effect either. Shortfall stated: 3 of 4 memory runs have trials (run 2's generation timed out). The one consistent change is Word2Vec: 0/3 without memory, 2, 2 and 1 of 3 in the three memory runs.

### Per task (3 attempts each)

| Task | Control | Run 1 | Run 3 | Run 4 | Placebo |
|---|---|---|---|---|---|
| build-word2vec-pipeline | 0/3 | **2/3** | **2/3** | **1/3** | 0/3 |
| apex-brightpath-market-share | 0/3 | 1/3 | 0/3 | 2/3 | 1/3 |
| cattrs compositional changelog (reference solution scores 0) | 0/3 | 0/3 | 1/3 | 1/3 | 0/3 |
| automationbench marketing content gap analysis | 2/3 | 2/3 | 1/3 | 1/3 | 1/3 |
| enterpriseops CSM | 2/3 | 2/3 | 0/3 | 2/3 | 1/3 |
| automationbench sales partnership contract | 1/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| cookie-store compositional changelog | 1/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| apex-brightpath-seat-surplus | 0/3 | 0/3 | 0/3 | 1/3 | 1/3 |
| the other 7 (Eurogrid scores 0.83 every attempt, its maximum reachable reward per the maintainers) | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |

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
| Nov 5–7 | Run 2 (running), run 3, about 15–16 h each. Then the exposure arms, to about Nov 8 |
| Nov 5–11 | Audit of the real pipeline. Draft on incoming data |
| **Nov 11** | **Go/no-go:** submit with the runs finished, stating the shortfall, or move to EASE (Jan 22) |
| Nov 12–14 | Full draft review, 4-page fit, anonymized artifact |
| Nov 15 | Submit to FORGE |
| After FORGE | Better generator, then EASE |

**If Qwen can't drive Hermes in the smoke test,** we stop and decide. The fallback is the Codex route, which is public code but not a published leaderboard row.

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
