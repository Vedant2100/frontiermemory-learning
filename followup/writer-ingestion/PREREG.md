# Follow-up: where does the memory writer lose knowledge? (pre-registration, draft)

Status: DRAFT, not yet frozen. Nothing in this folder has run. Frozen when the owner approves; after that, changes go in the amendments log at the end, dated, before the data they affect.

## 1. What this is, and what it is not

The failure analysis (`results/failure-analysis/REPORT.md`, sections 4.2 to 4.4) traced 19 requirements whose information the task does not give. For most of them the earlier runs held the information, and it was lost before it reached the notes. The writer's sessions showed how:

- first-message extraction;
- parsers that misread two of the corpus's three log formats;
- sampling a few files per group;
- truncating what was printed.

That is a trace, not a test. This follow-up tests it by changing what the writer sees while keeping the writer the same.

**This is not a benchmark run.** The main experiment followed the official FrontierMemory setup with one permitted change, the local model. This follow-up deliberately modifies the memory-generation harness. Its results are never pooled with, reported as, or compared on equal terms against the main experiment's arms or leaderboard numbers. Section 7 says how it is kept apart.

The question is about the writer only: given the same corpus, model and `/learn` request, how much of the needed knowledge reaches the notes under each ingestion condition, and at which stage it stops. Whether better notes help the task agent is a separate, optional second stage (section 9) with its own amendment before it runs.

## 2. Fixed across all conditions

- **Model:** Qwen3.8-27B on Ollama, the same build and serving settings as the main experiment, effort `max`.
- **Harness:** Hermes at the main experiment's pinned ref `d923a5eb`, `/learn`, the same `LEARN_REQUEST` text, the same disabled toolsets. The same local-server watchdog settings (protocol v4, D100).
- **Corpus:** v1.1, all 750 files. No file is added, removed or edited in content. Condition B changes only the format in which the same content is presented (section 3).
- **Budget:** the main experiment's 6-hour generation limit. The same GPU allocation (2 GPUs) and node.
- **Output handling:** the same skill export and the same `check-memory`.

## 3. Conditions

Each condition changes one thing relative to the previous one.

| | Condition | What changes | What Qwen still decides |
|---|---|---|---|
| A | Original `/learn` | Nothing. Baseline | Everything: which files to read, how to parse them, what to keep |
| B | Uniform, complete inputs | `/evidence/inputs/` holds a faithful rendering of each corpus file in one plain format: every user turn, agent message, tool call, tool result and verifier result, in order, untruncated. Same 750 files, same file stems, same request text. No new tool and no prompt change | Which files to read, how much to print, what to keep |
| C | B plus guaranteed exposure | As B, plus one file, `/evidence/digest.md`, holding every user turn after the first and every verifier feedback line from all 750 files, each labelled with its source file. One added sentence in the request points to it | Which lessons to keep |
| D | Oracle excerpts (diagnostic) | As B, plus `/evidence/excerpts.md` holding the passages the failure-analysis tracers identified for the 19 requirements, mixed with an equal number of passages relevant to none of them, in random order. One added sentence points to it | Which lessons to keep, from evidence chosen with hindsight |

**Why B changes the files, not the tools.** A new tool would need a tool description or a prompt change, which is a second difference from A. A uniform rendering puts the same content in a format Qwen's own scripts cannot misparse. Qwen can still sample, skip or truncate, and those choices are what the exposure stage measures.

**Why C's digest is task-blind.** The digest is built by a fixed rule over the corpus alone: all follow-up user turns and all verifier feedback. It never uses the 15 held-out tasks, their prompts or the 19 requirements. The rule does come from the failure analysis, which found that the lost conventions sit in follow-up turns; that is hindsight about where knowledge lives in a record, not about which knowledge matters. A retrieval rule that used the held-out task prompts would give the writer information the main experiment's writer never had. It is out of scope here, and would be a separate, labelled condition.

**Why D has distractors, and what it can claim.** Without distractors D only tests whether Qwen copies what it is handed. With them it tests whether Qwen picks out the lessons. D's passages were chosen by tracers who knew the requirements, so D is an upper bound on synthesis, never a deployable condition, and it is reported in its own table.

**Sequencing.** Stage 1 is A against B. C and D run only after stage 1 is analysed, under a dated amendment that confirms or adjusts them in light of B.

## 4. Sessions and sample size

The three existing writers under A differ widely: of the 19 requirements, 7 never reached run 1's and run 4's writers and 14 never reached run 3's. Run 2 hit the 6-hour limit and produced no notes. The variation between sessions of one condition is as large as the effects of interest, so every condition gets **5 sessions**.

- **A:** runs 1, 3 and 4 count as A sessions only if the gate (section 8) confirms the same Hermes ref, Ollama build, model digest and watchdog settings. Run 2's timeout counts as an A outcome (section 6). Then A needs 1 new session to reach 5 (runs 1 to 4 plus one). If anything differs, A gets 5 new sessions and the old runs are reported separately.
- **B:** 5 new sessions.
- **C, D:** 5 each, if run.

Stage 1 therefore costs 6 to 10 sessions, each up to 6 hours on 2 GPUs, run one at a time.

## 5. Measurement

### 5.1 Requirement set, frozen before any session

**Primary set:** the 19 scored requirements whose information the task does not give, under the outcome-blind prompt labels: awilix explicit and implicit R1; Word2Vec R1 to R3; cattrs R6; cookie store R3 and R5; customer delivery R7 to R9; DAPT R3 to R10. One of them, cattrs R6 (`default_factory` called once per call), has no corpus source; it is reported but cannot be gained, and the model meets it in 29 of 30 trials anyway.

**Secondary set:** the 34 requirements the task gives, that failed at least once, and for which the corpus holds evidence, mainly lessons from other tasks that say where to look ("read the meeting notes", "search mail before computing"). The failure analysis found most failures there. They are measured the same way, as a secondary outcome.

### 5.2 Answer key, frozen before any session

For each requirement, the corpus passages that carry its information, taken from the failure-analysis trace (`causal/stages/<task>.json`, private), each identified by file and turn. The key is frozen and hashed before the first session; its hash goes in the amendments log. It is private, because it quotes the gated corpus.

### 5.3 Stages, per requirement per session

| Stage | Question | How measured |
|---|---|---|
| Corpus | Is the information in the corpus? | The answer key. Fixed, the same for every session |
| Reader | Does the input format present it intact? | A: the raw file, as Qwen's own scripts printed it (part of exposure). B to D: verified once, before any session, by a round-trip check of the renderer on all 750 files (section 8) |
| Exposure | Did Qwen see it? | Did any of the key's passages appear in a tool output Qwen received during the session (`learn.json`)? Matched by exact substring after whitespace normalisation, by a script frozen with the key. "Partly" if only some of the passages appeared |
| Generation | Do the notes hold it? | Outcome-blind labels: yes, partial or no, and whether the notes carry a misleading rule for it. The labeller gets the notes and the requirement only, never the condition, the session or any outcome. Labels by the same brief as the main analysis (`causal/blind-labels.json`), two labellers, disagreements resolved by a third |

### 5.4 Outcomes

**Primary**, per session:

- **E:** number of the 19 requirements exposed (fully, or partly at half weight);
- **G:** number held in the notes (yes counts 1, partial 0.5).

**Secondary**, per session:

- the same counts on the secondary set;
- misleading rules;
- note length in tokens;
- session duration and timeout;
- per requirement, the stage at which it stopped (the 7 / 5 / 6 / 1 split of the failure analysis, by condition).

## 6. Analysis

- **H1:** B exposes more of the 19 than A (E, B > A).
- **H2:** B's notes hold more of the 19 than A's (G, B > A).
- **Test:** a one-sided exact permutation test over sessions. With 5 against 5 the smallest attainable p is 1/252. Report the difference in means with a bootstrap interval over sessions, and the per-requirement table.
- **Timeouts:** a session that hits the 6-hour limit without notes counts as E as measured from its log and G = 0. It is not rerun and not dropped. Run 2 is such a session. The number of timeouts per condition is reported, since a fuller input may make sessions longer.
- **Decision rules for stage 2:**
  - If B raises E but not G, the loss is in synthesis or prioritisation; run D before C.
  - If B raises neither, ingestion format is not the binding limit; run C.
  - If B raises both, run C to see how much selection adds.
  - Each is a dated amendment before it runs.
- **No pooling:** conditions are compared session against session. Counts are per distinct requirement, never summed over requirement-trials, and the A sessions are never merged with B's into one figure.

## 7. Isolation from the main experiment

The main experiment's data, disk, code and results are not touched.

- **Disk.** The follow-up never boots the main guest disk (`/scratch/$USER/fm-vm/disk.qcow2`). It boots a copy-on-write overlay in its own directory (`/scratch/$USER/fm-vm-followup/`) whose backing file is the read-only frozen copy made by `official/vm/freeze-disk.sbatch`. Writes go to the overlay only. The backing file stays read-only, and its hash is checked before and after each session.
- **Code.** Everything lives in `followup/writer-ingestion/`:
  - its own VM helper (a copy of `official/vm/lib.sh` with the root changed);
  - the renderer, the digest builder, the exposure matcher;
  - a harness subclass in its own module.

  Nothing under `official/`, `frontiermemory/` or `results/` is edited. The Hermes ref and the `frontier-memory` package are used as pinned.
- **Jobs and outputs.** Its own jobs directory inside the overlay (`jobs-followup/`), and job names prefixed `fmw-`. Logs go to `followup/writer-ingestion/logs/` and results to `followup/writer-ingestion/results/`.
- **Git.** Before the first session, the main experiment's final state is tagged `main-experiment-final`. Follow-up commits touch only `followup/`, so a diff against the tag shows the main experiment unchanged.
- **Data.** The corpus is mounted read-only. Renders, digests, excerpts, the answer key and session logs that quote the corpus are private (`~/fm-extract-20261116/followup/`), never in git; only counts are committed.
- **Shared resources.** Sessions run under the same `fm-serial` singleton job name as every other GPU job, so they never overlap another job. Never more than 2 GPUs, the disk checks of protocol v4, and no 1-GPU job while a 2-GPU job is pending.
- **Reporting.** Results are written up as a follow-up study with this pre-registration, and never added to the main experiment's tables, figures or arm list.

## 8. Gate, before any counted session

1. **Renderer round trip.** On all 750 corpus files, every text field of the raw file appears in its rendering, in order, and the rendering adds only structural labels. Per format (the codex format with its environment turn first, opencode, and the third), report file counts, turn counts and any field the renderer drops. Zero drops is required.
2. **Configuration match.** Hermes ref, Ollama build, model digest, effort and watchdog settings are logged and compared with the main experiment's generation logs. This decides whether runs 1 to 4 count as A sessions (section 4).
3. **Exposure matcher validated.** On runs 1, 3 and 4, the matcher reproduces the failure analysis's exposure findings for the 19 requirements. Differences are explained before the key is frozen.
4. **One uncounted B session** at the full 6-hour limit, to check that the larger inputs do not break the session or the export. Its results are discarded and reported as a gate result only.
5. **Answer key and labeller brief frozen and hashed.**

## 9. Optional stage 2: do better notes help the task agent?

Only if stage 1 finds a gain in G, and under its own amendment. The plan, for that amendment to confirm:

- the best stage 1 condition's notes, listed exactly as in the main experiment;
- the same 15 tasks, 3 attempts per session's notes, a control slice rerun to check for drift;
- primary outcome at the requirement level (the content test on the 19), not strict passes.

The failure analysis bounds what strict passes can do: at most 13 to 19 of 45 per arm even with all missing information supplied.

## 10. Not covered

- Other models or harnesses.
- Retrieval that uses the held-out tasks.
- Whether the 19 requirements are a fair test of memory. The five never-met requirements are being investigated separately; if that investigation finds a specification defect in any of them, the amendment log will say whether it stays in the primary set.

## Amendments log

| Date | Change | Before which data |
|---|---|---|
| | | |
