# FrontierMemory study: plan of action

*Updated Nov 2, 2026. Target: FORGE 2027 Data & Benchmarking, due Nov 15 ([call](https://conf.researchr.org/track/forge-2027/forge-2027-data-and-benchmarking-track)). Earlier study: [pilot archive](results/pilot-v1-README.md).*

## Summary

- **The problem:** our first study used a custom memory generator, Codex, Apptainer and our own runner. Any result about memory gains could be blamed on that setup, so it can't say anything about the benchmark's real pipeline.
- **The decision:** restart the whole experiment on the official setup. Only the model differs. The first study becomes a pilot and is never pooled with the new data.
- **The paper:** an audit of FrontierMemory that traces where memory's value can be lost: corpus → generation → harness → agent → grader. It shows what a score can and can't tell you.
- **Biggest risk:** time. The full run may take 7.5–12 days on one GPU server, which puts Nov 15 at risk. The decision point is Nov 11.

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
| Nov 2–3 | Records and docs (this file). Build the VM and Docker. CPU only |
| Nov 3–4 | Network probe. Reference-solution check on all 15 tasks |
| About Nov 4 | Old jobs finish. GPU smoke test: does Qwen work with Hermes? Lock the preregistration |
| Nov 5–14 | Counted runs, in order: no-memory control, then run 1, run 2, run 3 |
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

1. **APEX judge key:** 3 tasks are graded by an official OpenAI judge, at a few dollars. Without a key, those 3 stay ungraded. Task outputs go to OpenAI; no corpus data does.
3. **Optional insurance:** apply for [Modal academic credits](https://modal.com/pricing) in case the VM route fails.
4. **Cluster check:** consider mentioning the VM to the admin. It stays within our allocation, and we haven't seen a policy on it.
