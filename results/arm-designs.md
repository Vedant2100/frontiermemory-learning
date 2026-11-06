# Experiment arms: worked examples, lineage, and soundness (2026-11-06)

**Purpose.** For every planned arm, this document gives:
- what one complete run looks like on a real task;
- which published work it follows, or why it is new;
- what was changed to follow that work faithfully;
- where it is implemented.

**Related files.**
- Run order, hypotheses and checks: `results/preregistration-arms.md` (a draft awaiting approval).
- Code: `official/fm_local/` (`arm_*`, `build_*`, `cue_plugin/`, `*_local.py`), `official/vm/derive_arm.py`, `scripts/analyze_arms.py`.
- Tests: `official/tests/test_arms.py` (standard library) and `test_arms_harness.py` (real Harbor 0.24.0 and pinned `frontier_memory` classes against a fake container).

**Status.** Nothing here has run. Only rows marked "observed" are measured data. Counts only: no corpus or memory text.

**Sources.** Every source below was opened at least to its abstract page.
- **[check table]:** a number taken from a full-text reading; confirm it in the paper before citing.
- **[verified]:** spot-checked again on its abstract or documentation page.
- Most 2026 sources are arXiv preprints, not peer reviewed.

## How the arms relate to the official benchmark

Every arm is a plug-in to FrontierMemory's own pipeline, not a separate one:
- **Official commands and hook:** the official `frontier-memory generate-memory` and `run-tasks` commands, through the documented `--harness module:Class` hook (`frontiermemory/docs/submitting-a-harness.md`).
- **Same set script:** the set script is derived by exact replacements from the one the counted main-study sets use. So tasks, attempts, limits, judge, no-reward reruns, scoring, summary, key audit and audits are the same code.
- **Departures:** what each arm changes, and whether that stays inside the official rules (`frontiermemory/docs/rules.md`), is in the fidelity table of `results/preregistration-arms.md`.
- **Within the official rules:** the generator arm and the Codex and Claude Code arms.
- **Deliberately outside them:** the delivery arms change the fixed task agent's loading. The placebo, records and recency arms change what memory or corpus the agent gets. That change is what each of them tests.

## Two facts from the pinned code that shape the designs

- **The official Hermes memory is all skills.**
  - `/learn` exports only skills.
  - `MEMORY.md` is a generated list of links: `# Learned Hermes skills` then `- [name](skills/name/SKILL.md)` (`frontier_memory/hermes_dream.py`, `export_skills`).
  - At start Hermes shows MEMORY.md as a block, plus an `<available_skills>` index of each skill's frontmatter name and description, grouped by category. The category is the skill's parent folder, with an optional `DESCRIPTION.md` heading (Hermes d923a5eb, `agent/prompt_builder.py`).
  - Skill bodies are read only on demand. This is Anthropic's progressive disclosure: "At startup, only the metadata (name and description) from all Skills is pre-loaded" (Agent Skills best practices **[verified]**).
- **Hermes has a native hook for appending to tool results.**
  - `transform_tool_result` runs after every tool call, before the result enters the context (`model_tools.py`).
  - The bundled `security-guidance` plugin uses it to append warnings; it is a port of Anthropic's Claude Code plugin.
  - The cue arm uses the same hook.

**Measurement caveat found while building this:**
- **The old measure's flaw:** `exposure_measure.py` counts a skill as "indexed" when its name appears anywhere in the system prompt. HM's MEMORY.md block also names every skill folder, so for HM that count cannot separate the index from MEMORY.md.
- **The fix:** the new `arm_check.py` counts only inside `<available_skills>`.
- **A related risk for HM:** Hermes collapses some category names to "names only". If a learned skill landed in one of those categories, HM showed it without a description. To be checked on the run 1 to 4 memories (paths only).

## The running example: `customer-delivery-contextual-preferences`

A public coding task: the agent edits a repository and must commit its patch. The verifier runs 188 hidden checks (162 existing + 26 new). Reward is 1 only if all pass, and the task encodes contextual user preferences.

Observed so far (the verifiers' own counts):

| Set | Attempts | Passed | Hidden checks passed | Agent time | Input tokens |
|---|---|---|---|---|---|
| A0, no memory | 3 | 0 | 184–186 of 188 in every attempt (D111) | 32, 55, 36 min | 7.6M, 13.6M, 10.0M |
| HM run 1 (13 files, 62 KB) | 3 | 0 | 184–186 of 188 in every attempt | 34, 36, 34 min | 7.6M, 10.9M, 8.7M |

**What run 1 showed across all tasks:**
- the agent opened a memory file in 15 of 45 trials;
- 5 of 7 passes came without opening memory (D111).

**This task in the evidence arm:** the coverage relation matches no corpus runs to customer delivery, so the evidence arm gives it nothing, which is the same as A0. That is reported, not hidden.

**The outer pipeline every arm shares:**
1. memory generation, if the arm has one;
2. Harbor starts the task container;
3. the task agent works through the relay to Qwen;
4. the agent stops;
5. the official verifier scores the commit;
6. checks: serving, key audit, summary and arm check.

Below, "turn 0" is what the model sees in its first request.

## The arms, most promising first

### 1. Placebo memory: is it the content? *(standard control; our matched version is stricter than the precedent)*

**One run on customer delivery:**
- **Before the run:** `build_placebo.py` turns run 1's memory into a placebo with the same number of skills and files, each file the same byte length. Names become `note-01`… and content comes from Moby-Dick (Project Gutenberg #2701, public domain).
- **Turn 0:** the instruction, a MEMORY.md listing `note-01…note-NN`, and an index of "note-01: Reading notes, part 1." and so on. That is the same shape and size as HM.
- **During the run:** the agent may open the notes and finds nothing relevant.
- **Checked:** the placebo's index is the one shown; byte-for-byte size match.
- **Compared with:** HM1 and A0.

**Why it matters.** Without it, an HM or E-all difference could come from a longer, memory-shaped prompt rather than from what the memory says.

**Lineage.**
- Du et al., "Context Length Alone Hurts LLM Performance Despite Perfect Retrieval", Findings of EMNLP 2025, arXiv 2510.05381: length alone changes performance.
- VibeMemBench (Fan et al., arXiv 2609.23570) **[verified]**: a fixed distractor passage of everyday sentences ("There is a cat sleeping on the sofa") in place of the memory, on three solvers. Results ranged from −3.4 to −0.7 points against memory-off, and every interval crossed zero.
  - Its authors: "The distractor passage is not matched to the frozen record in token count"; a stricter length-controlled condition is described separately (their Table 12), and the paper does not say whether it was run.
- Ours is matched in size and shape, and memory-shaped: skill files, frontmatter and an index.

### 2. Read-first: does the agent use what it has? *(adapted)*

**One run:** HM, plus one fixed sentence in the system prompt: "Saved memory from earlier work is available: … Before you start the task, check them and open any saved skill that may be relevant." The agent can then open skills through `skill_view` or read the files.
- **Checked:** the sentence and the memory block are in the saved system prompt.
- **Compared with:** HM1.

**Why it matters.** It targets the observed bottleneck: memory was opened in only 15 of 45 trials.

**Lineage.**
- Letta, "Benchmarking AI Agent Memory: Is a Filesystem All You Need?" (blog, Aug 2025): the agent was forced to search its files first, through tool rules.
- Anthropic's Skills design leaves loading to the model's judgment **[verified]**.
- The FrontierMemory blog reports a learned skill that was "never loaded" **[verified]**.

**Difference from Letta's design.** We ask in prose; we do not force it. Forcing would need Hermes tool rules, a larger change to the task agent.

### 3. Cue-triggered delivery ("System 1/2") *(new mechanism; closest prior work is LLM-gated)*

**One run:**
- **Turn 0:** nothing from memory, as in E-none. The memory folder is on disk but not advertised.
- **During the run:** the agent calls tools. The fm-cue plugin compares each call's tool name and arguments with every skill's name and description.
- **Firing rule:** a skill fires when they share ≥ 2 terms that are lowercase, at least 4 letters, and not on a fixed list of generic and path words. The skill's full SKILL.md is then appended to that call's result, at most once per skill.
- **Direct opens:** opening a skill directly counts as fired, with nothing appended.
- **Checked:** the plugin ran in every trial; activations and inserted bytes are logged.
- **Compared with:** HM1.

**Fixed during testing.** Words from the memory's own paths (`skills`, `SKILL.md`, `memories`, `hermes`) had made reading one memory file fire an unrelated skill. They are now on the stop list.

**Lineage.**
- Closest: Wu et al., "Remember When It Matters: Proactive Memory Agent for Long-Horizon Agents", arXiv 2607.08716, 2026 **[verified]**. A separate memory agent decides each step whether to inject a reminder; selective injection beat passive exposure, always-on injection and retrieval.
- Kim et al., "Agent Memory Distillation", arXiv 2608.07169: memory retrieved on tool-call errors.
- FLARE (Jiang et al., EMNLP 2023) and DRAGIN (arXiv 2403.10081) trigger on model confidence or information need. Ours is a static lexical rule, so it is *not* a replication of either.

**What is new.** A deterministic, model-free trigger over the agent's own tool calls; offline-authored skills as the payload; delivery inside the tool result through Hermes's native hook; once per skill. Frame it as a cheap baseline for LLM-gated proactive memory.

### 4. Scoped loading by BM25 *(follows the retrieval baselines)*

**One run:**
- **Before the run:** rank run 1's skills by Okapi BM25 (k1 1.2, b 0.75) between the task's instruction and each full SKILL.md, and keep the top 3.
- **Turn 0:** MEMORY.md plus an index of just those 3 skills. All files stay on disk.
- **Checked:** the index holds exactly the selected skills; scores and digests are in the arm report.
- **Compared with:** HM1.

**Lineage.**
- SkillRouter (Zheng et al., arXiv 2603.22455) **[verified]**: "removing body reduces Hit@1 by 37.3pp for Qwen3-Emb-0.6B, 38.7pp for Qwen3-Emb-8B", and 44.0 for the 8B pipeline (Section 3, Figure 1). So we rank on bodies.
- Liu et al., arXiv 2604.04323: skill gains shrink under realistic retrieval.
- BM25 is the standard baseline in MemoryAgentBench and LongMemEval.
- k = 3 follows SkillsBench (arXiv 2602.12670): 2–3 focused skills beat larger bundles.

**Replaced.** The earlier metadata-overlap rule.

### 5. Evidence: the task's related raw runs *(adapted from oracle settings)*

**One run:**
- **Setup:** no generated memory. The corpus runs that the benchmark's coverage relation links to this task are placed in `/tmp/hermes/records`, with one pointer line: "Records of N earlier agent work sessions on tasks like this one … are in /tmp/hermes/records."
- **The relation:** `scripts/corpus_coverage.py`, which reproduces the published coverage totals, D73.
- **Customer delivery:** 0 related runs, so no files and no pointer. Word2Vec gets 66.
- **Checked:** file count and pointer.
- **Compared with:** A0, and HM1 for reference.

**Lineage.**
- LongMemEval's oracle setting (Wu et al., ICLR 2025) gives only the evidence sessions.
- Letta's filesystem study gives the history as files.

**Difference.** Our relation is the benchmark's coverage rule, not hand labels, so it is "related runs", not ground-truth evidence.

### 6. Raw corpus as files: does generation add anything? *(follows He et al.'s raw condition)*

**One run:** as evidence, but with all 750 corpus runs (115 MB).

**Lineage.**
- He et al., "Is Progressive Disclosure All You Need for Long-Context Agents?", arXiv 2607.17598 **[verified]**. Raw navigation ties skill packs on one book with strong harnesses and collapses at library scale.
- Letta's filesystem study.

**Disclosure.** This gives the agent the gated corpus, which is a benchmark change.

### 7. Generator: better memory from the official hook *(adapted; within the official rules)*

**One run:**
- **Generation:** one fresh generation with the official Hermes `/learn` and the official request, plus three fixed sentences. Delivery is HM.
- **Turn 0:** HM's view of that new memory.
- **Checked:** the generation's recorded request ends with the added rules.
- **Compared with:** A0 and HM1.

**The three rules and their sources.**
1. Descriptions say what the skill does and when to use it, with specific key terms. Anthropic's authoring guide: "should include both what the Skill does and when to use it" **[verified]**. The FrontierMemory blog's "never loaded" skill had a generic description **[verified]**.
2. Keep each preference, environment fact and failure mode as its own item; do not merge or drop items. ACE (Zhang et al., ICLR 2026, arXiv 2510.04618): itemized updates against "brevity bias".
3. A few focused skills. SkillsBench.

**Tuning.** None: the rules are fixed from these sources, not tuned on task results.

**Related.** MemSkill (arXiv 2602.02474), ExpeL (AAAI 2024), Agent Workflow Memory (arXiv 2409.07429), Dynamic Cheatsheet (arXiv 2504.07952).

### 8–11. Harness comparison: Codex (C0/CM) and Claude Code (K0/KM) *(follows the same-model design)*

**One run of CM:**
- **Setup:** the repo's own `MemoryCodex` seeds run 1's memory as native Codex memories (`memory_summary.md`). The model is the same local Qwen, through the relay's Responses API.
- **C0:** no memory, with the memories feature still on.
- **K0/KM:** Claude Code with auto-memory (`MEMORY.md` first), through the relay's Messages API.
- **Before counting:** each harness passes its own full gate: customer delivery and APEX with memory, then awilix without memory to its full limit.

**Fixes found in the pinned code.**
- **Codex timeout:** Codex's built-in `openai` provider has a 300 s stream idle timeout that config cannot override. Codex's config reference: "Built-in provider IDs … are reserved and cannot be overridden"; default `stream_idle_timeout_ms` 300000 **[verified]**. That is the same cut that made Hermes give up in gate 1 (D100). `codex_local.py` routes through a custom provider with 900 s, matching the Hermes fix.
- **Claude Code model tiers:** Harbor points Claude Code's background "haiku" and subagent tiers at the main model only when it sets the base URL itself. `claude_code_local.py` sets it there, so no call asks for a Claude model. (The second cluster's adapter sets it afterwards, so its background calls would still ask for a Claude model.) `API_TIMEOUT_MS` is 1800 s, Hermes's per-call limit.

**Lineage.**
- Terminal-Bench (Merrill et al., arXiv 2601.11868) **[verified]**, Table 2: the same model across harnesses. GPT-5 scored 49.6 % with Codex CLI against 33.9 % with Mini-SWE-Agent; Claude Sonnet 4.5 scored 40.1–42.8 % across four harnesses. Its conclusion: "model selection is usually more important than agent scaffold".
- HAL (arXiv 2510.11977): scaffold × model interactions.
- Gloaguen et al., "Evaluating AGENTS.md", arXiv 2602.11988 **[verified]**: always-on context files did not raise success and cost over 20 % more.

**How to report.** A harness × local-model interaction, with 3 attempts where Terminal-Bench used 5 or more. Cross-harness differences are descriptive.

### 12–13. Recency, variants a and b *(adapted from MemoryAgentBench; scored on the memory, not on tasks)*

**Why the first design was replaced.** The planned design swapped versions of packages that tasks pin. Measured on the corpus: 0 relevant runs mention a task-pinned package at the task's version (counts only), so there is nothing to swap.

**One run:**
- **Corpus copy:** `build_recency_corpus.py` copies the corpus and appends one user step to pairs of related runs, which are timed ATIF trajectories. The older run gets a stale value and the newer run the current value of the same synthetic preference, with the same wording and no "this replaces…".
- **Example:** "User feedback for future build-word2vec work: name the final report or summary file with the prefix FMxxxxxx…".
- **Fact pairs:** up to three per family, which gives 7 facts in 3 families on corpus v1.1. Variant b swaps the two host files' names, so read order flips while timestamps do not.
- **Generation:** one generation per variant.
- **Scoring:** `recency_probe.py` scores each fact as current only, stale only, both, or neither.
- **No task trials:** the verifiers do not test these facts.

**Lineage.**
- MemoryAgentBench FactConsolidation (Hu, Wang & McAuley, arXiv 2507.05257): an original and a rewritten fact, scored directly. It ties recency to position.
- LongMemEval's knowledge-update category.
- Variants a and b separate position from time.

### 14. Categorized index *(adapted; least likely to matter)*

**One run:** HM, but run 1's memory skills are indexed under three of Hermes's own categories (a folder, plus a `DESCRIPTION.md` heading):
- "Saved memory: user preferences and conventions to follow";
- "… facts about environments, tools, paths and versions";
- "… procedures and workflows that worked before".

Classification uses fixed keyword counts over each skill's name and description; a skill with no keyword hit goes to procedures. The content is unchanged.
- **Checked:** every memory skill is indexed under a heading.
- **Compared with:** HM1.

**Lineage.**
- Categories: the FrontierMemory blog's own memory files (`user.md`, `environment.md`, task skills) **[verified]**, and CoALA (Sumers et al., TMLR 2024; preferences and environment facts are both "semantic", skills "procedural").
- Li, arXiv 2601.04748: grouping helps past a critical library size. With about 10 skills, a null result is likely, so this arm runs last.

### Already queued in the main study: E-none and E-all

- **E-none:** files on disk, nothing shown.
- **E-all:** every file in the system prompt.
- **Lineage:** Lost in the Middle (TACL 2024), Retrieval meets Long Context (ICLR 2024), Evaluating AGENTS.md, He et al.'s raw condition.
- **To report:** cost (tokens, time) next to pass rate, and where each injected file sits in the prompt.

### Post hoc: dose

Pass rate by how much memory the agent saw at start. No new run and no test:
1. E-none and cue: none;
2. scoped: top 3;
3. HM and categorized: full index;
4. read-first;
5. E-all.

Precedents: SkillsBench (focused beats exhaustive); Evaluating AGENTS.md (length binning).

## What is verified, and what only a real run can show

- **Verified without the GPU:**
  - Every design was checked against the pinned Hermes, Harbor and FrontierMemory source.
  - 54+ tests pass; one set runs the real Harbor and FrontierMemory classes against a fake container.
  - An independent review found 4 defects, all fixed with tests.
  - Every cited number was confirmed in the paper itself.
- **Only a real run can show:**
  - Hermes loading the cue plugin in the container;
  - Codex and Claude Code working through the relay to Ollama;
  - the placebo built from the real run 1 memory;
  - whether the server acts on each harness's effort setting.
- **How to get those first:** `STAGE=checks` runs only the effort probe (`official/vm/effort_probe.py`), the two harness gates, and every arm's one-trial end-to-end check. That is about a day of GPU, against about 8 for all counted sets. It runs before committing to the full run.
- **Effort probe, how:**
  - It sends the settings each harness actually sends ("xhigh" from Hermes and "max" from Codex on the Responses API, and both Messages forms) and reports status and reasoning size.
  - It also answers the main study's open item: whether effort reaches the model.
  - Which Messages form Claude Code sends is not observable here, because the relay logs no bodies.
- **Measurement caveat, impact checked:**
  - The over-count of "skills indexed" in `exposure_measure.py` is in no reported number. README finding 6 and the paper use the file-probe count ("1 of 13 files shown").
  - The exposure none-arm check is unaffected, since MEMORY.md is not shown in that arm.

## Corrections to earlier statements

- **Claude Code background model:** my review of the second cluster's branch said Claude Code's background model would not be set. That holds for its adapter, which sets the base URL after Harbor's own rule would have applied. Done Harbor's way (this branch), all tiers are pinned.
- **Recency:** the pin-based design had no targets. The corpus has no superseded package versions for any task, consistent with `results/recency-check.md`.

## For the paper

Related work to cite:
- **"Same memory, different delivery" framing:** SkillJuror (Chen et al., arXiv 2606.11543 **[verified]**: skill content fixed, organization varied; progressive disclosure gave +4.1 % passing trials).
- **Context length and placement:** Lost in the Middle.
- **Always-on context files:** Evaluating AGENTS.md.
- **Proactive delivery:** Wu et al. 2607.08716.
- **Harness effects:** Terminal-Bench.
- **Recency:** MemoryAgentBench.
- **Length confound:** Du et al.
