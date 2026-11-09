# Colab memory-bottleneck pilot (2026-11-08)

**Status:** completed synthetic diagnostic on a Colab T4. This is **not** an official FrontierMemory task run or an estimate of its causal effects.

## Why this test

Separate the ability of a small open coding model to **use** a correct fact from whether a model can **generate** correct memory. Original FrontierMemory Qwen3.8-27B and gated corpus were unavailable in this clean T4 runtime.

## Setup

- GPU: Colab NVIDIA Tesla T4 15GB.
- Task model and memory author: Qwen/Qwen2.5-Coder-3B-Instruct, FP16, greedy decoding, same system instruction and model for all task arms.
- Repo was cloned at `99a7fca`; 33 memory-arm/measurement unit tests passed.
- Four *synthetic* Python-function tasks with related historical ticket descriptions, one generation per condition, 25 deterministic functional assertions in total. Each task's target prompt omitted its historical policy.
- No premium APIs. No gated benchmark task data. No model fine-tuning. Tests were implemented independently from the model's source code.
- Program execution was via isolated Python subprocesses with a timeout and checks for disallowed calls/imports.
- Conditions: (1) no memory, (2) task-length-matched generic placebo, (3) 3B-produced historical summary, (4) hand-written correct concise rule memory, (5) raw historical ticket text, (6) the same hand-written correct rule appended **directly to the user task** rather than delivered as separate memory.

## Results: number of assertions satisfied (one generated solution per task/arm)

| Task | No memory | Placebo | Generated memory | Correct concise memory | Raw history | Correct rule in task |
|---|---:|---:|---:|---:|---:|---:|
| Tenant-key normalization (6 tests) | 0 | 0 | 4 | 1 | 2 | 1 |
| Alert routing (7 tests) | 0 | 0 | 6 | 1 | 6 | 7 |
| Report-path convention (6 tests) | 0 | 0 | 0 | 1 | 3 | 6 |
| Incident ID convention (6 tests) | 0 | 0 | 0 | 0 | 0 | 6 |
| **Total (25)** | **0** | **0** | **10** | **3** | **11** | **20** |
| **Whole tasks passed (4)** | **0** | **0** | **0** | **0** | **0** | **3** |

## Evidence and interpretation

1. When a precise policy was unknown, baseline and generic filler scored 0/25; content helped partial performance.
2. The 3B generator sometimes distorted or truncated facts. For example, one tenant-key summary said its checksum should use the *normalized* string length rather than the stated original-trimmed length. This is direct evidence of **generation error** in the toy setup.
3. Even a correct concise rule, supplied in a separate memory section, yielded 3/25, so the model often failed to **apply** correct historical information. Raw related histories yielded 11/25.
4. Critically, putting exactly the same correct rule in the current **task instruction** gave 20/25 versus 3/25 with that rule in a labeled previous-memory section. This is evidence of **prompt-placement/conditioning sensitivity** in this toy model. It does *not* establish the same effect in Hermes's actual skill harness because this pilot did not use that harness.
5. All results are a **single stochastic sample of model behavior despite greedy decoding**, with no repeated runs, no statistical intervals, only 4 hand-designed tasks and 25 correlated assertions. Differences are descriptive, not estimates of a generalizable treatment effect.
6. This experiment does not identify which mechanism dominates FrontierMemory, and does not adjudicate the 27B worker versus Hermes generator. It motivates a factorial experiment that holds task model, harness, model effort, history, and tests fixed while varying memory-generation source and exposure/placement; verify memories against training data before scoring, and repeat across many tasks.

## Next valid confirmatory design (not executed here)

Use the real gated corpus, released FrontierMemory evaluation tasks, and the same Qwen3.8-27B + Hermes setup as the main study; compare no memory, ordinary /learn memory, verified distilled memories created only from training trajectories, raw task-relevant histories, and same verified memory force-injected into a fixed prompt slot. Audit both the *content* and the *exact model-visible payload*. Repeat for enough tasks and independent generations. Pre-register comparisons. This is the path to separating generation, access, and utilization without needing premium models.

## Provenance

Executed in connected Colab runtime on 2026-11-08; an in-runtime `/content/frontiermemory-pilot/pilot_results.json` contains the per-task outputs and tests, but the temporary Colab filesystem is not a permanent repository artifact. This report summarizes the confirmed outputs; it does not pretend to reproduce the official benchmark.
