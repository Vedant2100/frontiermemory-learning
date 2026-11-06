# Experiment arms: worked examples, prior work, and soundness (2026-11-06)

Purpose: before any further arm runs, (1) show concretely what one complete run of each arm looks like on a real task,
(2) tie each arm to the paper it follows, or say it is new, and (3) list promising arms we are missing.
Nothing here has been run unless it says "observed". Counts only; no corpus or memory text.

Sources: every paper below was opened at least to its abstract page (three literature passes plus spot checks of the
load-bearing ones). Items marked **[check table]** come from a full-text reading; confirm them in the paper before citing.
Most 2026 sources are arXiv preprints, not peer reviewed.

## The running example: `customer-delivery-contextual-preferences`

A public FrontierMemory coding task: the agent edits a repository and must commit its patch. The verifier runs
188 hidden checks (162 existing + 26 new). Reward 1 only if all pass; the task also encodes contextual user preferences,
which is what memory is supposed to supply. Observed so far (main study, verifiers' own counts):

| Set | Attempts | Passed | Hidden checks passed | Agent time | Input tokens |
|---|---|---|---|---|---|
| A0, no memory | 3 | 0 | 184–186 of 188 in every attempt (D111) | 32, 55, 36 min | 7.6M, 13.6M, 10.0M |
| HM run 1, official memory (13 files, 62 KB) | 3 | 0 | 184–186 of 188 in every attempt | 34, 36, 34 min | 7.6M, 10.9M, 8.7M |

So with and without memory the agent gets within 2–4 checks and scores 0. Every arm below asks whether a different
way of delivering (or producing) the same memory closes that gap. Across the whole of run 1, the agent opened a memory
file in 15 of 45 trials, and 5 of 7 passes came without opening memory (D111); Hermes shows MEMORY.md plus a skill index
at start, i.e. 1 of 13 files' text.

## One run of each arm on that task

Every arm follows the same outer pipeline: (memory generation, if any) → Harbor starts the task container → the task agent
works through the local relay to Qwen → the agent stops → the official verifier scores the commit → our checks
(serving, key audit, summary). Only the step marked ▶ differs.

| Arm | ▶ What differs in this run | What the agent sees at turn 0 | What can change mid-run |
|---|---|---|---|
| **A0** (observed) | No memory directory | Task instruction only | Nothing |
| **HM** (observed) | Official Hermes memory loader | Instruction + MEMORY.md text + index of skill names/descriptions | Agent may `read` a skill file itself |
| **E-none** | Memory uploaded but MEMORY.md block and memory-skill index removed | Instruction only (same as A0) | Agent can still find and open the files with tools, unprompted |
| **E-all** | HM view + every memory file's full text appended, sorted by path (≤100k tokens) | Instruction + all 13 files (~62 KB ≈ 15k tokens) | Nothing new to deliver; it is all there |
| **Cue** | Nothing shown at start; a plugin watches each assistant turn | Instruction only | When the agent's text/tool arguments share a word (≥4 letters, not a stop word) with a skill's name/description, that skill's full text is appended once to the next tool result. Illustration (not observed): if a tool call's arguments and a skill's description share a word, that skill's text is appended to that call's output |
| **Scoped** | Before the run, keep only skills whose own scope metadata shares ≥2 words with the instruction | Instruction + MEMORY.md + a shorter index (only matched skills) | Same as HM, over the smaller set |
| **Categorized** | Same index as HM regrouped under "User preferences / Environment facts / Procedural skills" | Same bytes as HM, reordered under headings | Same as HM |
| **C0 / CM** | Codex CLI replaces Hermes; CM gets HM run 1's memory through the official Codex adapter | Codex's own loading rule (survey estimate: ~21% of an M3-size memory) | Codex reads files itself |
| **K0 / KM** | Claude Code replaces Hermes; KM as above | Claude Code's loading rule (survey estimate: ~48%) | As above |
| **Generator** | A different memory-generation harness writes the memory; delivery stays HM | HM view of a different memory | As HM |
| **Recency** | Generation reads a corpus copy with superseded facts inserted | HM view of the resulting memory | As HM; scored by whether the patch follows the current fact |

## Prior work and soundness, arm by arm

Verdicts: **Follows** = matches a published design; **Adapted** = published idea, our mechanism differs (say so);
**New** = no direct precedent found (state what was searched).

### E-none: memory on disk, nothing shown — *Adapted*
- He et al., "Is Progressive Disclosure All You Need for Long-Context Agents?", arXiv 2607.17598, 2026: a "raw" condition
  (documents on disk, read/grep only) vs skill packs and hybrid RAG, three harnesses, InfiniteBench. Raw ties on a single
  book with strong harnesses and collapses at library scale.
- Letta, "Benchmarking AI Agent Memory: Is a Filesystem All You Need?" (blog, Aug 2025): history only in files, agent forced
  to search first; 74.0% on LoCoMo (self-reported).
- Difference: theirs expose raw text; ours exposes curated memory with the index removed. No paper removes a memory index
  while keeping files. Sound as defined; describe it as "files reachable, nothing advertised".

### E-all: everything in context — *Adapted* (well grounded)
- Liu et al., "Lost in the Middle", TACL 2024: accuracy depends on where the relevant item sits in a long context.
- Xu et al., "Retrieval meets Long Context LLMs", ICLR 2024: retrieval vs long context.
- Gloaguen et al., "Evaluating AGENTS.md", arXiv 2602.11988 (2026): always-on context files for coding agents generally did
  not raise success and cost >20% more inference.
- Changes to follow them faithfully: (a) report cost (tokens, time) next to pass, as Gloaguen et al. do; (b) record the
  position of each injected file, since path order puts relevant files at arbitrary depth (Liu et al.). No need for a
  second ordering arm at 15 tasks.

### Cue-triggered delivery ("System 1/2") — *New mechanism; closest prior is LLM-gated*
- Closest: Wu et al., "Remember When It Matters: Proactive Memory Agent for Long-Horizon Agents", arXiv 2607.08716, 2026.
  A separate memory agent decides each step whether to inject a reminder or stay silent; selective injection beats passive
  bank exposure, always-on injection and retrieval (+8.3 pp pass@1 on Terminal-Bench 2.0).
- Kim et al., "Agent Memory Distillation", arXiv 2608.07169: memory retrieved reactively on tool-call errors.
- FLARE (Jiang et al., EMNLP 2023) and DRAGIN (Su et al., arXiv 2403.10081) trigger retrieval from model confidence or
  information need; DRAGIN explicitly argues against static rules. Ours is a static lexical rule, so it is **not** a FLARE
  replication and must not be described as one.
- What is new: a deterministic, model-free word-overlap trigger over the agent's own text and tool arguments, offline
  skills as payload, delivery appended to the tool result, fire once per skill. Frame it as a cheap baseline for
  Wu et al.'s LLM-gated design. Fix before running: the preflight must require ≥1 insertion (today zero insertions pass).
- Optional faithful variant (Wu et al.): an LLM gate per step choosing remind/silent. It doubles model calls on the one
  GPU server, so it is the more expensive arm.

### Scoped loading — *Adapted, and the weakest design as written*
- Practice: Cursor rules (attach by file glob, or by the agent reading a description); AGENTS.md nearest-file precedence.
- SkillRouter (Zheng et al., arXiv 2603.22455): routing on name+description alone loses 37–44 points of Hit@1 vs using
  skill bodies **[check table]**. Liu et al., arXiv 2604.04323: skill gains shrink under realistic retrieval.
- Ours is a pre-run ≥2-word overlap on metadata only, which is the weak option these papers measure. Recommended change:
  rank skills by BM25 over skill **bodies** against the instruction, keep top-k (fixed k), and report routing recall.
  That follows SkillRouter/Liu et al. and is the standard retrieval baseline the memory benchmarks use.

### Categorized index — *Adapted; likely null at our size*
- CoALA (Sumers et al., TMLR 2024): episodic / semantic / procedural memory, a conceptual taxonomy.
- MIRIX (Wang & Chen, arXiv 2507.07957): typed stores, which change storage and retrieval, not just headings.
- Li, arXiv 2601.04748: skill selection degrades past a critical library size; hierarchy helps there.
- Our index has about ten memory skills, far below that size, and only headings change. Recommend **dropping** this arm,
  or relabelling to CoALA's categories if kept ("User preferences" and "Environment facts" are both semantic).

### Harness comparison (C0/CM, K0/KM) — *Follows* the same-model design
- Terminal-Bench (Merrill et al., arXiv 2601.11868, 2026): the same model run under several harnesses; it concludes model
  choice usually matters more than scaffold, with large exceptions **[check table: GPT-5 49.6% Codex CLI vs 33.9%
  Mini-SWE-Agent]**.
- HAL (Kapoor et al., arXiv 2510.11977): scaffold × model interactions.
- Gloaguen et al. confound harness with model; ours holds Qwen fixed, which is cleaner.
- To follow faithfully: deliver memory through each tool's native mechanism (the official adapters do), keep 3 attempts per
  cell (Terminal-Bench used ≥5; flag it), report it as a harness × local-model interaction, not as harness quality, and
  use paired per-task tests.

### Generator — *Adapted*
- MemSkill (Zhang et al., arXiv 2602.02474): a designer reviews cases where memory was wrong or incomplete and refines the
  memory-writing skills. Closest to "generator redesigned from failures".
- ACE (Zhang et al., ICLR 2026): generator/reflector/curator, incremental itemized updates; names "brevity bias" and
  "context collapse". ExpeL (AAAI 2024), Agent Workflow Memory (arXiv 2409.07429), Dynamic Cheatsheet (arXiv 2504.07952).
- FrontierMemory's own blog: a skill with a generic description was "never loaded"; imperative "use when…" descriptions
  were loaded. That is a citable design rule.
- To follow: ACE-style itemized updates plus the blog's description rule, developed on held-out data only. New part: the
  failure modes are delivery-aware and it is evaluated through the official generation hook with delivery fixed.

### Recency — *Adapted; the downstream scoring is new*
- MemoryAgentBench (Hu, Wang, McAuley, arXiv 2507.05257), FactConsolidation: counterfactual edit pairs, rewritten fact
  placed after the original, with "newer facts have larger serial numbers"; accuracy.
- LongMemEval (Wu et al., ICLR 2025): knowledge-update category; Zep (arXiv 2501.13956) invalidates superseded edges by time.
- To follow and fix their confound: insert each stale/current pair in both file orders, so "keeps the latest" is separable
  from "keeps the last read"; perturb only facts the verifiers depend on; first run a no-GPU probe of the generated memory
  (current, stale, both, neither). New: scoring by the task's own verifier instead of QA.

## Arms we are missing (ranked for 15 tasks, ~13 GPU-hours per arm)

1. **Placebo memory, size- and format-matched** (same file layout and byte count, irrelevant content). Separates "memory
   helps" from "a longer prompt or a memory-shaped prompt changes behaviour". Du et al., Findings of EMNLP 2025
   (arXiv 2510.05381): context length alone hurts. VibeMemBench (arXiv 2609.23570) used an untoken-matched distractor; do
   the matched version. Highest value: it makes HM and E-all interpretable.
2. **Raw corpus as files** (no generation; corpus files readable, nothing advertised). Tests whether the generation step
   adds anything; follows Letta's filesystem study and He et al.'s raw condition. Note: it gives the agent the gated
   corpus, so it is a benchmark change; disclose it.
3. **Read-memory-first instruction** (one fixed sentence telling the agent to read memory before starting). Motivated by
   our own data: memory opened in 15 of 45 trials. Precedent: Letta's forced-search tool rule; LongMemEval's reading
   strategies. Cheap and directly addresses the "never loaded" failure.
4. **Generator-model swap**: conflicts with the local-model-only rule; sensitivity only.
5. **Oracle/gold memory** (LongMemEval oracle, SkillsBench curated skills): needs hand-written memory for 15 tasks; risk of
   bias. Not recommended now.
6. **Dose/size**: analyse post hoc (shown bytes vs pass) instead of a new arm.

## What the free GPU window can hold

After the exposure arms, the main cluster is free for about two set-lengths before the Nov 11 go/no-go. Recommended, in
order: **placebo** (strengthens the FORGE reading of HM and E-all), then **read-first** or **cue** (after its insertion
check is fixed). Scoped (as BM25 top-k), generator, recency, raw corpus and the harness arms go to the follow-up paper.
Each arm needs a dated preregistration amendment and its own end-to-end check before counting.

## For the paper

Cite as related work: Lost in the Middle; Evaluating AGENTS.md; SkillJuror (Chen et al., arXiv 2606.11543), which holds
skill content fixed and varies only organization (progressive disclosure +4.1% passing trials), the closest precedent for
our "same memory, different delivery" framing; Wu et al. 2607.08716 for proactive delivery; Terminal-Bench for harness
effects; MemoryAgentBench for recency.
