# Follow-up: where does the memory writer lose knowledge? (pre-registration, draft 2)

Status: DRAFT, not yet frozen. Nothing in this folder has run, and nothing is scheduled: no GPUs are available now, and no session is queued until the owner says so. It is frozen when the owner approves. After that, every change goes in the amendments log at the end, dated, before the data it affects. Draft 1 (commit 1bc21f8) was revised after an independent methods review; section 12 lists what changed.

## 1. What this is, and what it is not

The failure analysis (`results/failure-analysis/REPORT.md`, sections 4.2 to 4.4) traced 19 requirements whose information the task does not give. For most of them the earlier runs held the information, and it was lost before it reached the notes. The writers' sessions show how:

- extraction from first messages only;
- parsers that misread the corpus's non-standard formats;
- sampling a few files per group;
- truncating what was printed.

That is a trace, not a test. This follow-up tests it by changing what the writer is given while keeping the writer the same.

**This is not a benchmark run.** The main experiment followed the official FrontierMemory setup with one permitted change, the local model. This follow-up deliberately modifies the input to memory generation. Its results are never pooled with the main experiment's arms or leaderboard numbers, never reported as them, and never compared with them on equal terms. Section 8 says how it is kept apart.

The question is about the writer only. Given the same corpus content, model and `/learn` request, how much of the needed knowledge reaches the notes under each input condition, and at which stage does it stop? Whether better notes help the task agent is a separate, optional second stage (section 10), under its own amendment.

## 2. Fixed across all conditions

- **Model:** Qwen3.8-27B on Ollama, effort `max`. The model digest is logged per session.
- **Harness:** Hermes at the main experiment's pinned ref `d923a5eb`, `/learn` through the official `generate-memory` command. The same `LEARN_REQUEST` text, the same disabled toolsets, and the local-server watchdog settings of protocol v4 (D100), set as environment variables by the follow-up's run script. Hermes installs its dependencies unlocked at run time, so each session logs `uv pip freeze` inside the sandbox.
- **Logging:** a wrapper around the `/learn` driver writes the conversation to disk after every turn, including the transcripts of delegated subagents. The official driver writes `learn.json` only when the session ends, which leaves a timed-out session with no record of what the writer saw (run 2 of the main experiment). The wrapper changes no message, tool or setting, and it applies to every condition.
- **Corpus content:** v1.1, all 750 files. No file is added or removed, and no text is added, removed or reordered within a file. Condition B changes only the container format of the non-standard files (section 3).
- **Budget:** the 6-hour generation limit, 2 GPUs, the same node.
- **Output handling:** the official skill export and `check-memory`.

## 3. Conditions

| | Condition | What changes | What Qwen still decides |
|---|---|---|---|
| A | Original `/learn` | Nothing | Everything: which files to read, how to parse them, what to keep |
| B | One standard format | The corpus is passed as a rendered copy in which every file uses the format most of the corpus already uses (ATIF JSON, one key variant). The 137 files in other formats are converted to ATIF JSON, losslessly and untruncated. Files already in that variant are byte-identical. Same file stems; the JSONL files gain `.json`. No new tool, no prompt change | Which files to read, how to parse and print them, what to keep |

**Why ATIF JSON and not plain text.** The corpus has at least five container formats:

| Format | Files |
|---|---|
| ATIF JSON, in 3 key variants | 613 |
| Codex JSONL | 45 |
| Claude Code JSONL | 45 |
| `user_message` JSONL | 26 |
| opencode JSON | 21 |

In the main experiment the writers explored with `json.load`. Converting everything to plain text would change the extension, the tooling and Qwen's parse strategy, and Qwen would then parse the new text labels with its own scripts. Moving the minority formats into the majority format removes only the heterogeneity that broke the writers' parsers. The rendered corpus is passed with `--corpus <rendered dir>` and its own `SHA256SUMS`, so B needs no harness change. Render labels use only the source's own role names; no label marks a turn as important.

**Stage 1 is A against B.** Conditions C (guaranteed exposure) and D (oracle excerpts) are designed in section 11. They run only after stage 1 is analysed, under a dated amendment.

## 4. Sessions

- **New sessions only.** Every A and B session is run new on the follow-up's environment, 5 of each, interleaved A B B A A B B A A B. The main experiment's runs 1 to 4 are not reused as A sessions: their dependencies floated, were not logged, and ran on a different disk state. They are reported alongside as historical context only.
- **Valid session.** A session counts if it ends in one of three ways:
  - exported notes;
  - the 6-hour limit;
  - an empty export.

  The last two count with G = 0 and E as measured from the incremental log.
- **Infrastructure faults are rerun.** These are an Ollama stall, HTTP 500s, `model_unavailable` or a relay error, each identified by the same log checks as protocol v4. A slot gets at most 2 reruns. A slot that fails three times is reported as missing, and the study goes ahead with the rest.
- **Cost.** In the main experiment, successful generations took 20 to 24 minutes, and run 2 hit the 6-hour limit. Budget 0.4 to 6 GPU-hours per session: 10 sessions, at most about 60 hours on 2 GPUs, run one at a time.

## 5. Measurement

### 5.1 Requirement set and clusters, frozen before any session

The primary set is the 19 scored requirements whose information the task does not give, under the outcome-blind prompt labels. They fall into six clusters, each resting on one source of evidence:

| Cluster | Requirements | Gainable |
|---|---|---|
| Awilix release tier | explicit R1, implicit R1 | yes |
| Word2Vec contract | R1 to R3 | yes |
| Cookie store conventions | R3, R5 | yes |
| Customer delivery preferences | R7 to R9 | yes |
| DAPT metric and verdict rules | R3 to R8, R10 | yes; R9, the port-scan verdict, is reported but not gainable: its expected answer is a specification defect (failure analysis, section 4.8) |
| Cattrs `default_factory` | R6 | no: no corpus source; the model meets it in 29 of 30 trials anyway |

The secondary set is the 34 requirements the task gives, that failed at least once in the main experiment, and for which the corpus holds evidence. These are mostly lessons from other tasks that say where to look. They are measured the same way.

### 5.2 Answer key, frozen before any session

The key is built from the failure analysis's corpus trace and then re-anchored to the corpus itself:

- For each requirement, the key lists one or more **information units**: the separate facts the requirement needs.
- For each unit, it lists **alternative passages**: every place in the corpus that carries it (the 30 identical DAPT feedback lines are one unit with 30 alternatives).
- Each passage is stored as an exact span: file, step, character offsets.

The tracers' quotes are a starting point only. In the review, 30 of 198 were not verbatim in the corpus, and 14 contained ellipses. The key is hashed when frozen, and the hash goes in the amendments log. It is private, because it quotes the gated corpus.

### 5.3 Stages, per requirement per session

| Stage | Question | How measured |
|---|---|---|
| Corpus | Is the information in the corpus? | The key. The same for every session |
| Reader | Does the input present it intact? | A: the raw files. B: checked once before any session by the renderer round trip (section 9) |
| Exposure (E) | Did Qwen receive it? | The matcher (5.4) over every tool output in the incremental log, subagents included |
| Generation (G) | Do the notes hold it? | Blind labels (5.5): yes, partial or no, and whether a misleading rule is present |

### 5.4 Exposure matcher, frozen with the key

1. Take every tool output Qwen received and decode it. Unwrap the JSON envelope (`output` or `content`), strip the line-number prefixes of file reads (`^\s*\d+\|`), unescape `\n` and similar escapes left by printed Python objects, casefold, and collapse whitespace. Normalise each key passage the same way.
2. A unit counts as exposed if any contiguous window of at least 60 characters from the unit-critical part of any of its passages appears in the decoded outputs.
3. A requirement is exposed if all its units are exposed, partly exposed if some are, and not exposed if none are.
4. Passages shorter than 60 characters are excluded, as are spans that occur in more than 50 corpus files (boilerplate, such as task prompts).
5. Known failure modes:
   - Qwen's own paraphrase of a passage is a false negative.
   - Text shared with a task prompt is a false positive, which the boilerplate rule limits.

   Both are reported.

### 5.5 Notes labels

- **Labellers:** two outcome-blind labellers per set of notes, with the brief used in the main analysis (`causal/blind-labels.json`). Disagreements are resolved by a third.
- **Scrubbing:** before labelling, file paths, file extensions and format words are removed from the notes, because B's notes could otherwise reveal the condition. Each labeller records a guess of the condition, and the guesses are reported as a blinding check.
- **What they see:** the notes and the requirement only, never the condition, the session or any outcome.

## 6. Outcomes

**Primary: G_c,** the cluster-weighted notes score of a session. For each of the five gainable clusters, average its requirements' scores (yes = 1, partial = 0.5, no = 0), then sum the five clusters, for a range of 0 to 5.

Weighting by cluster stops DAPT's eight requirements, which rest on one kind of feedback line, from deciding the result. One writer's print decision could otherwise move the raw count by eight.

**Secondary,** each reported with its own test and a Holm correction across the four:

1. **E_c:** the exposure score, cluster-weighted the same way.
2. The raw counts of the 19, for comparison with the failure analysis.
3. The same scores on the secondary set.
4. Misleading rules in the notes.

**Descriptive:**

- note length in tokens;
- session duration and timeouts;
- per requirement, the stage where the information stopped (the failure analysis's 7 / 5 / 6 / 1 split for run 1), by condition;
- the labellers' guesses of the condition.

## 7. Analysis

**H1:** B's notes hold more of the knowledge than A's (G_c, B > A).

**Test.** A one-sided exact permutation test over the 10 sessions. The smallest attainable p is 1/252. Report the difference in means with a bootstrap interval over sessions.

**Power.** The study can detect only large effects. In the main experiment the three writers were exposed to 11, 4 and 11 of the 19 requirements (by the tracers' reading), a spread of about 4 around a mean of about 9. With 5 sessions per condition, one-sided α = 0.05 and 80% power, the smallest detectable difference is about 6 to 7 of the 17 gainable requirements (19 less cattrs R6 and DAPT R9), about a third of the scale; on G_c that is about 1.5 of 5. A smaller difference is reported with its interval and not claimed.

**Decision rules for what follows.** Each is a dated amendment before its data:

- B raises E_c but not G_c: the loss is in synthesis or prioritisation. Run D next.
- B raises neither: the input format is not the binding limit. Run C next.
- B raises both: run C to measure how much selection adds.

**No pooling.** Conditions are compared session against session. Requirements are counted per distinct requirement and cluster, never summed over trials. The historical runs are never merged with new A sessions.

## 8. Isolation from the main experiment

The main experiment's disk, jobs, code and results are not written to.

**Disk.**

- The follow-up never boots the main guest disk (`/scratch/$USER/fm-vm/disk.qcow2`).
- It boots a copy-on-write overlay in its own directory, `/scratch/$USER/fm-vm-followup/`, created with `qemu-img create -f qcow2 -b <frozen> -F qcow2`.
- The backing file is the existing read-only frozen copy, `frozen-20261103.qcow2`, sha256 prefix `d3e79993` according to its freeze log. The gate confirms the file, its read-only mode and its full hash before the first session, and records the hash in this log.
- `official/vm/freeze-disk.sbatch` is never run: it boots the main disk read-write and rewrites the guest's Docker configuration.
- The frozen copy predates the main experiment's generations (Nov 5 to 7). That is acceptable because A and B both run new on the same overlay; the gate checks that generation works there.
- Before each session, check that the backing file is still read-only, and run `qemu-img check` on it. The full sha256, which takes minutes on 66 GB, is checked at the start and end of the study.

**VM helper.**

- `official/vm/lib.sh` hard-codes its root (line 3) and disk (line 16).
- The follow-up uses its own copy, `followup/writer-ingestion/vm/lib.sh`:
  - the root is `/scratch/$USER/fm-vm-followup`;
  - the seed directory and SSH key are copied into it;
  - the console and Ollama logs are written there;
  - the model directory is bound read-only (`:ro`), and the gate tests that Ollama still serves with it.

**Run script.** The follow-up does not reuse `official/vm/run-set-v1.sbatch`. Its own script, `followup/writer-ingestion/vm/run-session.sbatch`:

- runs generation only: no task trials, no judge key, no key audit;
- writes logs to `followup/writer-ingestion/logs/`;
- uses the guest jobs directory `jobs-followup/` and job names prefixed `fmw-`;
- never writes to `results/official`;
- stops only processes it started, recorded by PID, never `pkill -u $USER`.

**Code.** Everything else lives in `followup/writer-ingestion/`:

- the renderer;
- the logging wrapper;
- the exposure matcher;
- the labelling scripts.

Nothing under `official/`, `frontiermemory/` or `results/` is edited.

**Git.** The main experiment's final state is tagged `main-experiment-final` (commit 644de9f). Follow-up commits touch only `followup/`, so a diff against the tag shows the main experiment unchanged.

**Gated data.** The corpus is read-only. Renders, the key, incremental logs and anything that quotes the corpus are kept in `~/fm-extract-20261116/followup/` and never committed. Only counts go into git.

**Shared resources.**

- Each session runs under the `fm-serial` singleton job name, so it never overlaps another GPU job.
- Never more than 2 GPUs, and no 1-GPU job while a 2-GPU job is pending.
- The `/scratch` disk thresholds of protocol v4 apply to the overlay.

**Reporting.** The results are a follow-up study under this pre-registration. They are never added to the main experiment's tables, figures or arm list.

## 9. Gate, before any counted session

1. **Renderer round trip, all formats.** For all 750 files, check that every text field of the source appears in the rendering, in order, untruncated. Then confirm that the ATIF files already in the target variant are byte-identical. Report the files, turns and fields per source format and key variant. Zero dropped fields is required.
2. **Environment.** The overlay boots with the main disk untouched. The guest's frontiermemory tree and `.venv` are checked against the version the main experiment ran. Ollama serves the logged model digest from the read-only model bind. `uv pip freeze` is recorded.
3. **Matcher validation.** On the logs of the main experiment's runs 1, 3 and 4, compare the matcher with the tracers' exposure labels in a confusion table per requirement. The tracers searched by keyword, so their labels are a baseline, not ground truth. Each disagreement is resolved by reading the log, and the key or matcher is fixed before freezing.
4. **Logging wrapper.** One short uncounted session checks that the incremental log captures the parent and delegated transcripts, and that the session behaves as without the wrapper (the same tools, the same request).
5. **One uncounted B session** at the full 6-hour limit, to check that generation and export work with the rendered corpus. Its results are discarded and reported as a gate result only.
6. **Freeze.** The key, the matcher, the scrubbing rules and the labeller brief are frozen, and their hashes go in the log.

## 10. Optional stage 2: do better notes help the task agent?

Only if stage 1 finds a gain in G_c, and under its own amendment. The plan for that amendment to confirm:

- **Notes:** each condition's notes, listed exactly as in the main experiment.
- **Tasks and drift:** the same 15 tasks, 3 attempts, and a control slice rerun to check for drift.
- **Primary outcome:** at the requirement level (the content test on the 19), not strict passes. The failure analysis bounds strict passes at 13 to 19 of 45 per arm, even with all missing information supplied.

## 11. Conditions C and D (designed now, run only by amendment)

- **B′, the comparator for C and D.** C and D add a file and one sentence to the request. B′ is B plus a neutral file, an index of the corpus files with their sizes, and a matched sentence pointing to it. B′ needs its own sessions, so C and D are compared against B′, not B.
- **C, guaranteed exposure.** A digest built by a fixed rule over the corpus alone, never the held-out tasks or the 19 requirements:
  - human follow-up turns (user turns after the first that are not tool or system output);
  - verifier feedback lines;
  - each labelled with its source file;
  - capped at a fixed size, set in the amendment from the gate's measurements.

  A digest of every later user turn would be 1.29 million characters, larger than the model's context, and Qwen would sample it again. So C's exposure is measured, not assumed. The rule comes from the failure analysis's finding that the lost conventions sit in follow-up turns. That is hindsight about where knowledge lives in a record, and it is stated as such.
- **D, oracle excerpts (diagnostic).** The key's passages for the 19 requirements, plus an equal number of distractors drawn by a fixed rule from the same files, matched in length and kind (feedback-like or turn-like), in random order. D measures synthesis given hindsight-selected evidence. It is an upper bound, never a deployable condition, and it is reported in its own table.
- **Builder.** The official task builder copies only `inputs/` into `/evidence/`, so C, D and B′ need a custom builder. It is used for all three, to keep them comparable.

## 12. Changes from draft 1, after the methods review

| Draft 1 | Draft 2 |
|---|---|
| Exposure by exact substring of tracer quotes | A re-anchored key of units and alternative passages, with a decoding matcher and a 60-character window rule, validated by a confusion table |
| Runs 1 to 4 reused as A sessions; run 2's timeout counted | All A sessions new and interleaved with B. Runs 1 to 4 are historical: their dependencies floated, and run 2 left no record of what it saw |
| B renders every file to plain text | B moves only the 137 non-ATIF files into ATIF JSON; files already in the target variant are byte-identical |
| "Three log formats" | Five container formats and three ATIF key variants |
| Isolation as intent | Concrete: overlay command, the named frozen file, a VM helper and run script of the follow-up's own, read-only model bind, no `pkill`, `freeze-disk.sbatch` never run |
| Primary: raw counts E and G of 19 | Primary: G_c, cluster-weighted; E_c and the rest secondary with Holm correction; power stated |
| C's digest: every later user turn | Human follow-ups and verifier lines, capped, exposure measured; B′ as the matched comparator; custom builder |
| No logging change | Incremental logging, subagents included, in every condition |
| Labels blind to condition | Also scrubbed of paths and format words, with a blinding check |
| Valid session undefined | Defined, with a cap of 2 reruns per slot for infrastructure faults |

## Amendments log

| Date | Change | Before which data |
|---|---|---|
| | | |
