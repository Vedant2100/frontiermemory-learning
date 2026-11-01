# Harness exposure survey (2026-11-01)

Question: when a task harness loads a FrontierMemory memory folder, how much of it lands in the model's context, and is the rest only reachable by the agent searching? FrontierMemory allows up to 8 MiB per memory folder (`frontiermemory/src/frontier_memory/memory.py`, `MAX_BYTES`), and each harness seeds the folder through its native memory mechanism (`frontiermemory/src/frontier_memory/agents/`).

## Rules per harness

| Harness | Injected at start | Cap on injected part | Over the cap | Other files | Source |
|---|---|---|---|---|---|
| Codex CLI (FrontierMemory adapter) | `memory_summary.md` (adapter copies `MEMORY.md` if absent) into developer instructions | 2,500 tokens (≈4 bytes/token → 10,000 bytes) | Head + tail kept, middle replaced by "…N tokens truncated…" | On disk, agent can open | `openai/codex` `codex-rs/ext/memories/src/lib.rs` (`MEMORY_TOOL_DEVELOPER_INSTRUCTIONS_SUMMARY_TOKEN_LIMIT = 2_500`), `prompts.rs`; **measured**: 5,000 + 5,000 chars in all 1,484 logged requests (D50, D51) |
| Claude Code (FrontierMemory adapter) | `MEMORY.md` of the project's auto-memory folder | First 200 lines or 25 KB, whichever first | Not loaded at session start | Topic files read on demand with file tools | [code.claude.com/docs/en/memory](https://code.claude.com/docs/en/memory) |
| OpenAI Agents SDK (sandbox memory) | `memory_summary.md` into developer prompt | 15,000 tokens (≈60,000 bytes) | `truncate_text` keeps head + tail | `MEMORY.md` and `rollout_summaries/` searched with Shell | `openai/openai-agents-python` `src/agents/sandbox/capabilities/memory.py` (`_MEMORY_SUMMARY_MAX_TOKENS = 15_000`), `sandbox/util/token_truncation.py`; [docs](https://openai.github.io/openai-agents-python/sandbox/memory/) |
| Hermes Agent (FrontierMemory adapter) | `MEMORY.md` and `USER.md` as a frozen system-prompt snapshot | 2,200 / 1,375 chars are **write** limits only | Loaded in full ("never truncate a user's memories"); further writes blocked | Uploaded beside them; reachable with tools | `NousResearch/hermes-agent` `tools/memory_tool_store.py`; [docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory) |
| Letta Code (official leaderboard task harness) | Files at the memory root, every turn | 20,000 chars per file, 65,536 chars for root files (enforced on write) | Not known at load; Letta's FrontierMemory loader is not public | Subdirectories out of context until read | [docs.letta.com/letta-code/memfs](https://docs.letta.com/letta-code/memfs), `letta-ai/letta-code` `src/memory-constraints.ts` |

The Codex cap is 2,500 tokens, not 5,000 as one third-party write-up says. Our measured 10,000-character window matches 2,500 × 4 bytes.

## Same memory, different harness (`scripts/harness_exposure.py`)

| Memory | Harness | Bytes shown | Topics shown | Word2Vec topics shown |
|---|---|---|---|---|
| M3 (46,651 B, 324 topics) | Codex CLI | 10,001 (21%) | 83 | 0 of 4 |
| | Claude Code | 22,621 (48%) | 129 | 4 of 4 |
| | OpenAI Agents SDK | all | 324 | 4 of 4 |
| | Hermes | all | 324 | 4 of 4 |
| R25 (27,021 B, 116 topics) | Codex CLI | 10,001 (37%) | 65 | 1 of 3 |
| | Claude Code | 24,855 (92%) | 104 | 3 of 3 |
| | OpenAI Agents SDK / Hermes | all | 116 | 3 of 3 |

The simulated Codex count (83 of 324) matches what we measured in the request bodies, which validates the simulation.

## What this means

- What a memory *shows* depends on the harness as much as on the memory. On M3 under Codex, every Word2Vec success came from the agent searching; under Claude Code, the same topics would have been shown.
- The leaderboard's harness table compares memory generation **and** loading together (README: harness submissions may provide "native memory loading and task execution"). Differences between harness rows mix memory quality with exposure rules.
- FrontierMemory's protocol defines a no-memory control (README, `rules.md`), but the public leaderboard (frontiermemory.com, checked 2026-11-01) shows no no-memory row, no per-task results and no SD values. The paper must word this as "not reported", not "not defined".

## Open items

- Letta Code's load-time behavior for an oversized root `MEMORY.md` (M3 is 46,651 chars, over the 20,000 per-file limit). Its FrontierMemory loader is not public; ask Letta or test locally with Letta Code.
- Claude Code and Hermes rules are taken from current docs and source; versions pinned in FrontierMemory may differ (`DEFAULT_CLI_VERSIONS`).
