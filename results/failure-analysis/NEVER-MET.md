# The five never-met requirements: investigation results

Five requirements were never met in any of their 30 trials (3 attempts × 10 arms), so five tasks could not pass in any arm. This note records what the checkers test, what every trial did, where the needed information was, and whether each is a fair test of memory. It was written on 2026-11-23 from an investigation of all 150 trial-requirements, the task checkers, the reference solutions and the earlier-run corpus. The corrections it forced in `REPORT.md` are listed in that report's section 8.

The per-trial classifications are in `causal/out/never-met-trials.json` (150 rows: task, requirement, arm, trial, how the attempt failed, and whether a relevant rule was in front of the agent). The full version, with message-level evidence and corpus passages, is private (`~/fm-extract-20261116/causal/persistent/`), because the corpus is gated. No corpus text appears here.

"Verified" means the file was read or the computation rerun. Where something is inferred, it says so.

## Summary

| Requirement | Checker consistent with the reference? | What the 30 trials did | Information in the task? | In the earlier runs? | In any notes? | Verdict |
|---|---|---|---|---|---|---|
| Awilix explicit: bump `package.json` to 12.1.0 | Yes | None edited `package.json`; 4 wrote an "Unreleased" changelog entry, 1 a `v12.1.0` changelog heading | The tier, not the rule | 10 runs, always as a maintainer's instruction at the end | No | Fair test |
| Awilix implicit: the same, tier in a metadata file | Yes | None edited a version or changelog | The tier, in `.changes/awilix.yaml` | 5 runs, 4 with a pointer the task lacks | No | Fair test, harder than its corpus analogue |
| Customer delivery: runnable failure example in the docs | Yes, but narrower than the stated preference | None put a failure example in the docs; 17 wrote one in a scratch file | No | 2 runs, one with the same customer sentence | No | Mostly fair; a placement failure |
| DAPT: `has_port_scan = false`, `is_traffic_benign = true` | The reference passes by a detector the test's own comment contradicts, and hard-codes `benign` | All 30 answered scan = true after finding the sweep | No | A perfect feedback contrast, encoding the same expected answer | A vague rule in run 1, run 4 and blend | **Specification defect** |
| Eurogrid: average avoided curtailment 243,275.57 MWh | The positive criterion is right; the reference reports .56 and fails | 29 used the obvious method (228,025.94), 1 another (228,033.33) | Yes, in a notes document in the task's files | A "read the team's conventions" lesson from other tasks | No | Fair test of in-task search; the defect is in the reference only |

## 1. Awilix release tier, both variants

**The checker.** It passes only if the collected patch changes `package.json` to version 12.1.0. Committed and uncommitted edits both count. The hidden preference maps release tiers to version bumps (1–2 none, 3–5 patch, 6–8 minor, 9–10 major); the task is tier 7. The reference patch makes exactly that edit, and the oracle passes both variants.

**What the trials did.** Explicit variant, per arm:

| Attempt | Control | Placebo | Raw records | Blend | Run 1 | Run 3 | Run 4 | None shown | Read-first | All shown | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| No version or changelog edit | 3 | 2 | 3 | 2 | 3 | 3 | 2 | 2 | 2 | 3 | 25 |
| Changelog "Unreleased" entry, no version | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 0 | 1 | 0 | 4 |
| Changelog heading `v12.1.0`, `package.json` untouched | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 |
| `package.json` bumped | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

- **Agents noticed the tier and declined to act on it.** 20 of the 30 explicit trials mention the tier. By a heuristic (the tier mentioned within 400 characters of "bump" or "version"), 9 linked it to a version bump and declined, saying the release scripts own the version or that the tier was task metadata. One run 4 trial opened its notes specifically to find out what a release tier means and found nothing.
- **Closest miss.** A none-shown trial reasoned from ordinary semantic versioning that a new feature makes it 12.1.0, wrote that in the changelog, and left `package.json` alone.
- **Implicit variant.** No trial made any version or changelog edit. Three displayed the metadata file holding the tier and dismissed it as release metadata; 9 more saw the `.changes` path in a listing; 18 never saw it.

**Where the information was.**

- **Task:** the explicit prompt gives the tier but not the rule; the implicit task has the tier only in `.changes/awilix.yaml`.
- **Earlier runs:** ten maintainer sessions in four repositories state a tier and later say which bump to make. They are consistent with the rule, and tier 7 follows from tiers 6 and 8 both mapping to minor. But in all ten the bump came as the maintainer's instruction at the end; no agent bumped a version unprompted. In four of the five runs that keep the tier in `.changes/`, the maintainer tells the agent to look there. The implicit task gives no such cue.
- **Notes:** none of the three generations mentions tiers, bumps or versions. The raw-records arm staged no records for either awilix task.

**Verdict.** A fair test of memory. The rule is consistent across ten earlier sessions, the checker matches the reference, and nothing blocks the edit. Two caveats:

- The corpus teaches the rule only as an instruction, so the agent has to generalise from "the maintainer asked for this" to "do this unasked".
- 12.0.5 to 12.1.0 is also what plain semantic versioning gives a new feature, so the requirement is passable without the tier rule. The barrier is as much the model's reluctance to edit version files as the missing mapping.

**Smallest intervention and its test.** One note sentence giving the tier-to-bump mapping and telling the agent to edit the version file itself rather than leave it to release scripts; for the implicit variant, also "check `.changes/*.yaml`". Test design:

- run 1's notes plus that sentence, against run 1's notes plus a length-matched irrelevant sentence, both pasted into the prompt, 3 trials each;
- a third arm saying only "bump the version per semantic versioning when you add a feature", which separates a missing rule from a refusal to touch versions.

Risk that the rule is stated and still not applied: moderate, given the 9 trials that declined.

## 2. Customer delivery: a runnable failure example in the docs

**The checker.**

- **Where it looks:** files the patch touches under README, docs or examples, in JavaScript only. Markdown blocks marked `js` or unmarked count; TypeScript never counts.
- **What the code must contain:**
  - a container, an initializer and initialization;
  - a literal `.disposer(` call;
  - a thrown or rejected error, caught, whose cause or message is inspected.
- **How it runs:** it is executed with node and must exit cleanly within 20 seconds.

The reference adds a README block that does exactly that, and the oracle passes. The checker is narrower than the preference it implements:

- cleanup must go through `.disposer(`;
- TypeScript examples never count, although the library is TypeScript;
- the example must be in the docs.

None of these narrowings decided a trial here, because no trial put a failure example in the docs at all.

**What the trials did.**

| Attempt | Control | Placebo | Raw records | Blend | Run 1 | Run 3 | Run 4 | None shown | Read-first | All shown | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| No README, docs or example edit | 1 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 1 | 5 |
| README example of the success path only | 2 | 2 | 3 | 0 | 3 | 1 | 3 | 3 | 3 | 1 | 21 |
| Success-path example with a disposer, no failure | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 1 | 3 |
| Error snippet without container or disposer | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

- **The capability was there.** 26 of 30 trials wrote failure-path code with a disposer and cause inspection in their tests. 17 wrote a complete runnable failure-and-cleanup program, but in a scratch or `/tmp` file, outside the docs. These are the closest misses: the content existed and ran.
- **What kept examples out of the docs.** The four arms with run 1's notes edited the README in 11 of 12 trials, so the notes' "minimal changes" advice did not stop docs edits. Blend's task text told the agent to write a verification script under `/tmp`, and all three blend trials put the example there and made no docs edit.

**Where the information was.**

- **Task:** absent; the only cue is that the work is a customer delivery.
- **Earlier runs:** two maintainer sessions ask for one runnable failure or cancellation example, one of them with the same customer-delivery sentence (t0720) and a later request for a monotonic clock. That run's example was a TypeScript file under `examples/`, which this checker would not accept; a faithful copy of the precedent could still fail.
- **Notes:** none. Raw records: none staged.

**Verdict.** Mostly a fair test. The preference is stated twice in earlier sessions. The checker's literal demands (`.disposer(`, JavaScript, docs paths) go beyond what memory could teach, but they decided nothing here.

**Smallest intervention.** Test two note wordings against each other, 3 trials each, pasted into the prompt:

- **Generic,** as the earlier runs state the preference: include one runnable failure or cancellation example showing cleanup and the caller-visible error.
- **Checker-specific:** commit a JavaScript README example that registers a disposer, makes an initializer throw, catches it, and prints the cause.

If only the specific wording works, the checker's literalness is the binding constraint. Risk: low for the specific wording, since the agents already write this code; higher for the generic one.

## 3. DAPT: the port-scan verdict (specification defect)

**The checker.** An exact match on `has_port_scan = false` and `is_traffic_benign = true`. The test file's own comment on the expected value says there is no aggressive port scanning, defined as more than 500 ports on a single target.

**The reference.**

- `is_traffic_benign` is hard-coded to true.
- `has_port_scan` is true only if some source's traffic, taken as a whole, exceeds three thresholds: port entropy above 6 bits, a share of SYN-only packets above 0.7, and more than 100 distinct destination ports.
- The task was built "without embedded skills". The removed SkillsBench skill file is where those thresholds were stated.

**The capture, recomputed (verified).** A reimplementation of the reference detector on the task's capture found:

- 192.168.3.1 sends SYN-only packets to 1,000 distinct ports on 192.168.3.30.
- 1,085 of those 1,089 packets fall within one minute.
- The target answers with about 1,140 resets.

That meets the test comment's own definition of a scan, and any ordinary one. The reference still says "no" because the same host also ran an 8,465-packet SSH session, which dilutes its statistics over all its TCP traffic: port entropy 1.64 against the 6-bit threshold, SYN-only share 0.114 against 0.7.

Inferred: applied to the sweep's packets alone, the same thresholds give "yes".

**What the trials did.** All 30 answered `has_port_scan = true`, `is_traffic_benign = false`, and every one identified the sweep.

| | Control | Placebo | Raw records | Blend | Run 1 | Run 3 | Run 4 | None shown | Read-first | All shown | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Answered scan = true | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 30 |
| Had the notes' vague rule in front of it | 0 | 0 | 1 | 3 | 1 | 0 | 1 | 0 | 3 | 3 | 12 |
| Failed only this requirement | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 3 |

- **The rule:** "don't infer a scan from many destination ports alone; require evidence of aggressive scanning". Every one of the 12 trials that had it in front of them found that evidence and answered "yes".
- **The trial that came closest to "no":** a raw-records trial saw an earlier run that had answered "no", and dismissed it as a failing run.

**The earlier runs.** All 35 earlier DAPT runs failed. The 30 that answered "yes" received the feedback sentence behind the notes' rule; the 5 that answered "no" did not. The contrast is perfect, and no feedback contains a threshold. That contrast makes the expected answer learnable as what this grader rewards, not as a fact about the traffic.

**Verdict.** A specification defect:

- the expected answer contradicts the capture and the test's own comment;
- `benign` is hard-coded;
- the thresholds that would make "no" reproducible were removed with the skills.

It decided this requirement in all 30 trials and the whole task in 3. A note could flip it only by giving the answer.

**Fix.** Fix the task, not the notes: accept "yes" or drop the requirement, or restore the threshold rule with its denominator stated. As a memory test, only an answer-giving note would flip all trials, and the risk that a rule-based note is ignored is high, because on the evidence the model's reading is correct.

## 4. Eurogrid: the average avoided curtailment

**The checker.** An LLM judge with a positive criterion of 243,275.57 MWh and a negative criterion naming 243,275.56. Every saved rationale, for the oracle and for all 30 trials, applies only the positive criterion.

**Recomputed from the task's workbook (verified).** The team's method (the sum of the values divided by the sum of the per-MWh values over the six years) gives 243,275.56887, which rounds to .57. The obvious method, the mean of the per-year quotients, gives 228,025.94. The reference slide shows .56, a truncation, so the reference fails the positive criterion. A correctly rounded answer by the team's method would most likely pass.

**What the trials did.**

- All 30 met the other five checks. 29 reported 228,025.94 and one (all shown) 228,033.33.
- Two run 3 trials computed .57 as an alternative and chose the obvious method instead.
- The team's method is in a "standing team conventions" section of `Brainstorming.docx` in the task's own files. 23 trials saw the file's name in a listing, one made a metadata call on it, and none read it.

**Where the information was.**

- **Task:** given, but only by search.
- **Earlier runs:** none of this task. Other Brightpath runs carry the lesson "read the conventions section": the five that read it all passed, and the one that did not failed.
- **Notes:** none point there. The raw-records arm staged runs containing the section, but no trial read that part.

**Verdict.** A fair test of searching the task's own files, which memory can help only as a pointer. The rubric's defect affects the reference only and decided no agent trial.

**Smallest intervention.** A pointer note naming the document and section, against a placebo sentence, 3 trials each, recording whether the document was opened as well as the value. Fix the reference to .57. Risk moderate: 23 trials walked past the file name.

## 5. What this changed in REPORT.md

| Earlier claim | Corrected |
|---|---|
| No verifier defect decided any failure | DAPT's port-scan verdict is a specification defect; it decided that requirement in all 30 trials and the task in 3 |
| DAPT's verdict comes from unstated thresholds, recoverable by comparing feedback | The thresholds were removed with the task's skills, and the expected answer contradicts the test's own criterion |
| DAPT is the clearest case of agents ignoring their notes | The agents' reading was correct. Without DAPT, read partial or misleading notes failed 22 of 81 times |
| Five corpus runs keep the tier in `.changes`, as the implicit variant does | In four the maintainer points the agent there; no corpus agent bumped unprompted |
| Run 1's "minimal changes" advice works against customer delivery's docs example | Run 1's arms edited the README 11 of 12 times; only blend's `/tmp` instruction kept examples out of the docs |
| t0720 asked for nearly the example the checker wants | Its example was TypeScript, which the checker ignores |
| Eurogrid's negative .56 criterion fails the reference | The reference's truncated .56 fails the positive .57 criterion |

## 6. Verified and inferred

**Verified:**

- every checker reading;
- the oracle results;
- the DAPT recomputation on the capture;
- the Eurogrid recomputation;
- all 150 trial classifications;
- the corpus contrasts and counts;
- the contents of the notes.

The main session also independently checked the DAPT test comment, the hard-coded `benign`, the task's "without embedded skills" build and the per-trial tallies.

**Inferred or heuristic:**

- the count of trials that linked the tier to a version (a text-window heuristic);
- the README block classification;
- that a TypeScript or non-`.disposer` example would fail (read from the checker, not run);
- the entropy of the sweep's packets alone (arithmetic);
- how the APEX judge uses negative criteria;
- every risk estimate.
