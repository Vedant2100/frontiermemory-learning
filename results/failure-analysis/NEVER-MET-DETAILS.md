# The five never-met requirements: what the checkers test, what the 30 trials did, and whether memory could have helped

The full investigation behind `NEVER-MET.md`, with corpus passages, task-file quotes and message-level evidence. Included in the repository at the owner's decision (2026-11-23). Written 2026-11-23 by the investigating agent. Its conclusions were spot-checked by the main session (DAPT test comment, reference hard-coding, task built without skills, the recomputed capture statistics, trials.json tallies) and the corrections went into REPORT.md section 8 (commit 9af1094).

Per-trial classifications: `causal/out/never-met-trials.json` (150 rows, with per-trial evidence in `details`). Scripts: kept with the private data (they ran from a scratch folder) (`awilix.py`, `cdel.py`, `dapt.py`, `dapt_ref.py`, `eurogrid.py`, `fmload.py`); that is a scratch location and may be cleared.

Sources:
- Task definitions: `~/frontiermemory-experiment-20261024/data/tasks/frontier-memory/<task>/`. The extracted VM copy `data/home/fm/official/frontiermemory/data/tasks-fm/` has no tests, so the tests could not be diffed against what ran; every verifier message in the trial outputs matches the repo checker text.
- Trials: `~/fm-extract-20261116/data/home/fm/official/frontiermemory/jobs/<arm job>/<trial>/` (model.patch in `artifacts/logs/artifacts/`, verifier output in `verifier/`, reasoning in `agent/hermes-session.jsonl`, tool calls in `agent/trajectory.json`). "msg N" = hermes-session message index; "step N" = trajectory step.
- Corpus: `~/frontiermemory-experiment-20261024/data/corpus/v1.1/inputs/tNNNN.json[l]`.

## Summary table

| Requirement | Checker vs reference | 30 trials | In the task? | Corpus | Notes/records | Seen by a trial | Fair memory test? |
|---|---|---|---|---|---|---|---|
| Awilix explicit R1 | Correct; reference edits package.json 12.0.5 -> 12.1.0 | 0 bumped package.json; 1 v12.1.0 CHANGELOG heading; 4 "Unreleased" entry; 25 nothing | Tier given, rule absent | 10 runs, tier->bump consistent, always an explicit maintainer instruction at the end | None | Nobody saw the rule | Yes, by induction; target coincides with plain semver |
| Awilix implicit R1 | Same | 0 bumped, 0 changelog edits; 3 displayed the yaml | Tier in `.changes/awilix.yaml`, rule absent | 5 yaml runs, 4 with a maintainer cue the task lacks | None | Nobody | Yes, harder than its corpus analogue |
| Customer delivery R7 | Consistent with reference; narrower than its stated preference | 0 README failure examples; 21 success-path only; 3 success-path with disposer; 1 error snippet; 5 no docs; 17 wrote a complete failure+cleanup+cause program in scratch | Absent | t0720 (same cue sentence), t0567 | None | Nobody | Mostly; the literal checker would fail the corpus's own precedent (.ts example) |
| DAPT R9 | Reference passes by a detector its own test comment contradicts, and hard-codes benign | 30/30 scan=true, benign=false; all found the 1,000-port SYN sweep; 12 had the vague rule in front of them | Absent; thresholds were in SkillsBench skills, removed | Perfect contrast in 35 feedbacks | Vague rule in run 1, run 4, blend | 12 saw the rule; 1 saw a "false" answer in records | Specification defect; learnable only as grader behaviour |
| Eurogrid R3 | Positive criterion 243,275.57 correct; gold slide and reference show .56 (truncated), so the reference fails | 29 x 228,025.94, 1 x 228,033.33; 2 computed .57 and discarded it | Yes, in Brainstorming.docx (task_files override) | Pointer lesson: 5 EuroGrid runs read the conventions section, all PASS | None | 23 saw the file name, 1 a metadata call, 0 read it | Fair test of in-task search; defect in the reference only |

## 1. Awilix release tier (explicit and implicit), R1_release_tier_version_bump

### a. Checker

`tests/user_preference_verifier.py` (both variants identical) passes only if: `/logs/artifacts/model.patch` is non-empty; `/app/package.json` has `"version": "12.1.0"`; the patch contains `diff --git a/package.json b/package.json`; the patch has an added line matching `^\+\s*"version"\s*:\s*"12\.1\.0"\s*,?\s*$`.

`tests/user-preference.json`: "Internal release tiers 1–2 require no version change, 3–5 require a patch bump, 6–8 require a minor bump, and 9–10 require a major bump." Target: tier 7, package.json 12.0.5 -> 12.1.0.

The patch is collected as `git reset --soft <base> && git add -A && git diff --cached` (task.toml `[[verifier.collect]]`), so committed and uncommitted edits both count. Implicit: base `refs/tags/frontier-memory-task-base`; `test.sh` recreates the yaml fixture if the tag is missing.

Reference: `solution/solution.patch` lines 1–11 change 12.0.5 -> 12.1.0; same patch both variants. Oracle trials pass (`oracle-all/awilix-release-tier-explicit__CrvTTEu`, `...implicit__iAb8Z7b`).

Correct and consistent. 12.0.5 -> 12.1.0 is also ordinary semver for a backward-compatible feature; the repo has `npm run release:minor`. The barrier is the model's prior against touching the version, not only the missing mapping.

### b. 30 trials

Explicit, by arm (ctl, plc, evd, bld, r1, r3, r4, none, rf, all):

| Attempt | ctl | plc | evd | bld | r1 | r3 | r4 | none | rf | all | total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| No version or changelog edit | 3 | 2 | 3 | 2 | 3 | 3 | 2 | 2 | 2 | 3 | 25 |
| CHANGELOG "Unreleased" entry, no version | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 0 | 1 | 0 | 4 |
| CHANGELOG heading `# v12.1.0`, package.json untouched | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 |
| package.json bumped | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

20 of 30 explicit trials mention the tier. By heuristic (tier within 400 characters of "bump"/"version"), 9 connected it to a bump and declined (control 2, placebo 2, run1 2, blend 1, run4 1, readfirst 1). Examples:
- control 4nx388t msg 18: "Might mean the release process: the version bump is handled elsewhere; or it's a grader hint ... Let me ignore it"; msg 144: "I left the version and changelog untouched (the repo's release scripts own those)".
- placebo r5RTQ3w msg 18: "maybe it means I should bump the version? ... I think it's metadata for the task system".
- run1 bfJQsnT msg 109: "it's about the internal release of the eval, not an instruction to bump the version".
- run4 vD76mjd msg 141: "I won't bump the version (release scripts handle that)"; msg 174 guesses "v13.0.0 (a major feature)" and writes "Unreleased".
- run4 YShaxbA msgs 1–20 opened its notes to find what "release tier" means, found nothing, called it "task metadata (maybe a distractor, or indicating difficulty tier 7)".

Closest miss: noneshown vz66Ban msg 121 ("Since this is a new feature, it'll probably be v12.1.0"), wrote `# v12.1.0` in CHANGELOG.md, left package.json at 12.0.5. control fLywAtZ on customer delivery (msg 55) weighed bumping to 12.1.0 and declined.

Implicit: 30/30 no version or changelog edit. Yaml content displayed in 3 trials (control 9gDfvZS msg 145, run3 7KcdQvA msg 126, noneshown VrBGMhQ msg 17), all dismissed it. `.changes` path in a listing in 9 more; 18 never saw it.

Memory opened: explicit run4 YShaxbA, readfirst 9nrgBN9, P6zn8RP; implicit run3 xmEy4Aw, run4 B3A7kYh, dSCfKUa, readfirst XftrSGy, qxSBtW7. Nothing relevant in the notes.

### c. Where the information was

(i) Task: explicit gives the tier (last line of instruction.md); implicit only in `.changes/awilix.yaml`. The mapping is only in hidden tests. Blind label "absent", high.

(ii) Corpus (all gpt-5.6-sol):

| File | Tier | Where | Maintainer bump instruction |
|---|---|---|---|
| t0397 | 2 | request turn, step 11 | step 159 "ok, i don't think we need to bump the version for this one. keep `pyproject.toml` at `4.0a1`." |
| t0123 | 2 | `.changes` yaml; cue step 119 | step 256 "ok, i don't think we need to bump the version for this one." |
| t0667 | 5 | step 9 | step 109 "ok, bump the patch version for this one." |
| t0420 | 5 | yaml; cue step 61 | step 156 "ok, bump the patch version for this one." |
| t0254 | 6 | step 9 | step 264 "ok, bump the minor version for this one." |
| t0551 | 6 | yaml; cue step 78 | step 169 "ok, bump the minor version for this one." |
| t0202 | 8 | step 9 | step 286 "ok, bump the minor version for this one." |
| t0060 | 8 | yaml | step 302 "ok, bump the minor version for this one. Confirm the resulting `packages/vitest/package.json` version." |
| t0263 | 9 | step 10 | step 204 "ok, bump the major version for this one. It should go from `3.17.0` to `4.0.0`" |
| t0267 | 9 | yaml; cue step 94 | step 175 "ok, bump the major version for this one." |

Yaml cue in t0123, t0267, t0420, t0551: "what'd I set the internal release tier to again? I put the release metadata under .changes/." t0027: same awilix feature at 12.0.5, no tier, FAIL.

No agent bumped before being told in any of the ten (tool-call scan). In four of five yaml runs the maintainer points to `.changes/`; the implicit task has no cue. Tiers 1, 3, 4, 7, 10 never appear.

(iii) Notes: none in any generation (grep tier/release/bump/semver/package.json). Evidence arm: 0 records for both awilix tasks. Blend: explicit identical; implicit adds "Make minimal non-test source changes".

(iv) No trial saw the rule. Suggest downgrading implicit corpus status to "partial".

### d. Fair memory test, with the caveats above.

### e. Minimal intervention

Note: "When a request states an internal release tier (in the prompt or in `.changes/<pkg>.yaml` as `internal_release_tier`), bump the root package version in the same change: tiers 1–2 none, 3–5 patch, 6–8 minor, 9–10 major. Edit package.json (or pyproject) directly; do not leave it to release scripts." Implicit: "Check `.changes/*.yaml` before finishing." Test: run 1's notes + this sentence vs + length-matched irrelevant sentence, all-shown exposure, 3 trials each; a third arm "bump the version per semver when you add a feature" separates missing mapping from refusal to touch versions. Risk moderate.

## 2. Customer delivery, R7_pref_runnable_failure_example

### a. Checker

`tests/user_preference_verifier.py`, `async_lifecycle_example()`: candidates are patch-touched files matching `(^|/)(readme(?:\.[^/]*)?|docs?|examples?)(/|$|\.)`; Markdown fences with language in {"", javascript, js, node, mjs, cjs}; `.ts` excluded; `.js/.cjs/.mjs` files whole. `failure_shape`: `createContainer`, `.initializer(`, `.initialize(`, `.disposer(`, `.cause` or `.message`, throw/reject/abort, `catch`, and inspection of `.cause`/`.message` in `if (`, `assert` or `console.log/error(`. Written to `/app/.frontier-memory-customer-delivery-example.cjs|.mjs` with `'awilix'` -> `./lib/awilix`, run with node, exit 0 within 20 s.

Stated preference: "For asynchronous APIs, include a runnable failure or cancellation example that demonstrates cleanup and the caller-visible error."

Reference: two README `js` blocks; second registers `.disposer((database) => database.close())`, initializer throws, catches, checks `error.cause?.message` and `cleanedUp`. Oracle: "PASS user_preference.async_lifecycle_example: README.md#block-37: executed successfully".

Narrower than the preference: needs literal `.disposer(`; TypeScript never counts; must be in README/docs/examples. Decided no trial here.

### b. 30 trials

All 30: "no new user-facing JavaScript example matched the required behavior".

| Attempt | ctl | plc | evd | bld | r1 | r3 | r4 | none | rf | all | total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A. No README/docs/example edit | 1 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 1 | 5 |
| B1. README success-path only | 2 | 2 | 3 | 0 | 3 | 1 | 3 | 3 | 3 | 1 | 21 |
| B2. Success path with `.disposer(`, no failure | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 1 | 3 |
| C. Error snippet without container/initializer/disposer | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

B2: run3 TiNZtHZ, run3 aRcrcbw, allshown MVaeC3e. C: placebo MDRYkcG. Fence languages in added doc blocks: js 54, ts 5, unlabelled 1.

26 of 30 wrote failure-path code with `.disposer(` and `.cause` in jest tests. 17 wrote a complete runnable program (initializer failure, disposer, catch, `.cause`) to scratch (`/tmp/hermes/cache/scratch/*.js` or `/tmp/repro_init.js`) or ran it inline: placebo 2, evidence 2, blend 3, run1 1, run3 1, run4 1, noneshown 3, readfirst 2, allshown 2, control 0. Blend's three followed its prompt ("write a small reproduction/verification script to a file under `/tmp`"). 25 of 27 non-blend trials edited README; run 1's four arms 11 of 12.

### c. Where the information was

(i) Absent. Cue only: "I'm delivering this project to a customer as part of a contracting engagement."

(ii) Corpus:
- t0720 (Clack autocomplete, FAIL): step 11 "I'm delivering this to a customer as part of a contracting engagement." Step 72: "I need one runnable failure or cancellation example before approval. It should exercise the async resolver cleanup path and visibly show the error surfaced to the caller." Step 94: "The example covers the cancellation cleanup/error case, thanks." Step 257 asks for `performance.now()` over `Date.now()`. The agent wrote `examples/basic/autocomplete-async-cancel.ts`.
- t0567 (Boa engine, Rust, FAIL): step 196 "Add one runnable cancellation example before I approve it. It should actually cancel an evaluation, demonstrate the relevant cleanup/context reuse afterward, and show the cancellation error or reason surfaced to the caller." Wrote `examples/src/bin/evaluation_cancellation.rs`. No customer cue.

(iii) Notes: none. Evidence: 0 records. Blend: "Make minimal non-test source changes" + `/tmp` script instruction.

(iv) Nobody saw it. Corpus: "present for the preference, partial for what the checker accepts".

### d. Mostly fair.

### e. Minimal intervention

Checker-specific note: "When the user says the work is a customer or contracting delivery and adds an async API, commit a runnable failure example in README.md (a ```js block using `require('awilix')`) that registers a service with `.disposer(...)`, makes an initializer throw, catches the error, and prints `error.cause.message` and that cleanup ran. It will be executed." Test generic corpus wording vs checker-specific, all-shown, 3 trials each. Risk low for the specific note.

## 3. DAPT, R9-port-scan-false-and-benign-true

### a. Checker

`tests/test_outputs.py` lines 77–79, 432–450: exact match `has_port_scan` == "false", `is_traffic_benign` == "true". Comments: `"is_traffic_benign": "true",  # This is clean enterprise traffic`; `"has_port_scan": "false",  # No aggressive port scanning (>500 ports on single target)`.

Reference `solution/solve.sh` lines 206–273: `is_traffic_benign` hard-coded "true". `has_port_scan` true only if an IPv4 source with >= 50 TCP packets has port entropy > 6.0 bits over all its TCP, SYN-without-ACK ratio > 0.7 over all its TCP, and > 100 unique destination ports.

Reimplemented without scapy (`dapt_ref.py`, `dapt_ref.out`) on `environment/packets.pcap`:
- 114,099 packets, 32,620 IPv4 TCP.
- 192.168.3.1: 9,555 TCP, 1,000 unique dst ports, entropy 1.644, 1,089 SYN-only, ratio 0.114 -> scan=False. Top dst port 22 with 8,465 packets.
- No source passes; reference has_port_scan = False.
- 192.168.3.1 -> 192.168.3.30: 1,000 unique SYN-only dst ports; 1,085 of 1,089 SYN-only in one 60 s window; 192.168.3.30 sends 1,140 RSTs.

task.toml: "SkillsBench dapt-intrusion-detection, materialized without embedded skills." Removed `solution/skills/threat-detection/SKILL.md`: "Port scanning is ONLY detected when **ALL THREE** conditions are true" (entropy > 6.0, SYN-only > 0.7, unique ports > 100).

Inferred: over 192.168.3.1's SYN packets alone entropy ~log2(1000) ~ 10 bits and SYN ratio 1.0, so thresholds applied to the scanning traffic still give true.

### b. 30 trials

| | ctl | plc | evd | bld | r1 | r3 | r4 | none | rf | all | total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| scan=true, benign=false | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 30 |
| Vague rule in front of the agent | 0 | 0 | 1 | 3 | 1 | 0 | 1 | 0 | 3 | 3 | 12 |
| Failed only R9 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 3 |

Exposure: blend in prompt; allshown via Hermes config (`agent/hermes-config.yaml` lines 293, 530); run1 bbiW8Po (msg 46), run4 h2eaBBf (msg 6), readfirst LQ9g3es, ihjGXpp, pPizqx2, evidence s7EZzRz (msgs 31, 33). All 12 answered true.

Failed only R9: run4 h2eaBBf, readfirst ihjGXpp, evidence s7EZzRz. s7EZzRz msg 11 saw "has_port_scan,false" (t0221); msg 30: "t0221 has has_port_scan=false, while others are true — t0221 might be a partial/failing run." allshown vCxq3ut msg 23: "999 different SYN destination ports were swept against `.3.30` within roughly a 1.3-second window". blend JWdQPiG msg 34 cites DAPT2020's port-scan phase.

### c. Where the information was

(i) Absent. Instruction: "`has_port_scan`: mallicious port scanning", "`is_traffic_benign`: nothing clearly malicious". `environment/scripts/*.py` not copied into the image.

(ii) Corpus, all 35 DAPT runs FAIL:

| Final has_port_scan | Port-scan sentence in feedback | Runs |
|---|---|---|
| true | yes | 30 |
| false | no | 5 (t0221, t0417, t0422, t0673, t0696) |

| Final is_traffic_benign | Benign sentence | Runs |
|---|---|---|
| false | yes | 31 |
| true | no | 4 (t0417, t0422, t0673, t0696) |

Port-scan sentence (e.g. t0010 step 18): "Do not infer port scanning from the dataset name or an aggregate count of many destination ports alone; require evidence that establishes aggressive scanning." Benign: "Set `is_traffic_benign` from the supported attack flags rather than from the dataset name." No threshold in any feedback.

(iii) Notes: run 1 `references/family-pcap.md:64`, `failure-modes.md:24`; run 4 `references/contracts.md:163`; blend prompt. Run 3 nothing. Evidence: 35 records staged per trial; only s7EZzRz read feedback and a "false" record.

### d. Specification defect.

### e. Fix the task (accept true or drop R9, or restore thresholds with the denominator stated). As a memory test only an answer-giving note would flip it; risk high.

## 4. Eurogrid, R3-average-avoided-curtailment-MWh

### a. Checker

`tests/grading_config.json`, verifier `ver_435820a7a3e44262aae51a14ec7ca4d7`: criterion "States the Average Avoided Curtailment for Germany-North combination is 243,275.57 MWh"; negative "States ... is a value other than 243,275.56 MWh". LLM judge via external runner. All rationales read apply only the positive criterion.

Workbook `Curtailment_and_Redispatch_Cost_Dataset.xlsx`, sheet `Avoided_Curtailment_Value`, Germany-North 2020–2025: sum(value EUR)/sum(value per MWh EUR) = 243,275.56887 -> .57; mean of per-year quotients = 228,025.93697 -> .94. Gold slide: "Avoided Curtailment: 243,275.56" (truncation). Oracle rationale: "The agent reported 243,275.56 MWh, not 243,275.57 MWh ... Not met."

### b. 30 trials: all passed the other five checks (0.8333, as the oracle). 29 x 228,025.94; 1 x 228,033.33 (allshown). Brainstorming.docx name seen in 23, metadata call 1 (readfirst ahRpqp6 step 28), content read 0. run3 cUqvkUJ step 30 printed "Alt: sum(value)/sum(price)" = 243,275.57; run3 nPsqEke msg 27 chose 228,025.94 over 243,275.57.

### c. Task gives it by search: `environment/task_files/filesystem/9) Working folders/Maelin/Brainstorming.docx` adds paragraphs 91–120, "Data reading notes – standing team conventions". Para 96: "Start on the euro side: add up the pair's Avoided_Curtailment_Value_EUR across its six annual records – that total is the numerator. Then divide that total by the sum of the pair's Value_per_MWh_EUR values." Para 97: "No per-year averaging: nothing fancier than that – the division of the two sums is the whole trick." Corpus: no run of this task; the conventions section with other entries; t0009, t0079, t0347, t0374, t0488 read the header, all PASS; t0232 did not, FAIL. Notes: none point there. Evidence staged t0009, t0232, t0347; not read.

### d. Fair test of in-task search; reference defect only.

### e. Pointer note to the doc section; fix gold to .57. Risk moderate.

## 5. Where REPORT.md was wrong (all corrected in commit 9af1094)

1. Stage 7 = 0 and "Verifier defects. One": DAPT is a ground-truth defect.
2. DAPT ">500 ports" comment cited as the threshold; by it the capture is a scan; skills removal omitted.
3. Release tier `.changes` runs: four of five have a maintainer cue; no unprompted bumps.
4. Customer delivery "minimal changes" claim overstated (run 1 arms 11/12 README edits; only blend 0/3).
5. t0720's example was `.ts`, which the checker ignores.
6. Eurogrid: reference fails the positive criterion; no rationale shows the negative one used.
7. Missing: awilix 12.1.0 equals plain semver.

## 6. Verified vs inferred

Verified: checker readings, oracle passes, DAPT reference result on the pcap, Eurogrid recomputation, per-trial classifications, corpus quotes and contrasts, notes contents. Inferred: "linked tier to version" counts (regex window), README block classification, `.ts`/non-`.disposer` failure (read, not run), SYN-only entropy (arithmetic), APEX negative-criterion use, risk estimates.
