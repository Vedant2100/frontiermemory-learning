# Cluster 2 preregistration: official FrontierMemory pipeline with harness comparisons

**Status: User-approved draft, amended for parity review on 2026-11-05; this revision awaits user review. No counted trial may start yet.** Before any counted trial, the finalized policy and audit code must be committed on branch `cluster2`, all required gates must pass, and that approved commit must be tagged `prereg-c2`.

Prepared 2026-11-05 for the separate `frontiermemory-cluster2` study on bender. This study has its own controls, memory generations, gates, preregistration, and results. Its measurements will not be pooled with or presented as replications of the main study.

## Question and scope

The primary question is whether generated memory improves strict task pass rate for the official Hermes pipeline with the local Qwen model. Exploratory questions are whether that effect differs under Codex and Claude Code, how much memory exposure changes Hermes performance, and whether alternative delivery rules change Hermes performance.

The experiment uses the official task runner and pinned task release, subject to the recorded cluster 2 deviations below. The model is local; this study does not estimate frontier-model or leaderboard performance. The pilot and main-study results are excluded. Alternative memory generators and recency/corpus perturbations are outside this preregistration; each requires its own design, approval, and preregistration before implementation or trials.

## Fixed environment

- **Code:** official FrontierMemory commit `9af28c2f8210779f442aa36a1d73553630441af5`; Harbor 0.24.0. Every run records the cluster2 commit, handoff revision, task manifest, and relevant artifact digests. An incoming main-study handoff update stops the launch until reviewed and incorporated as required.
- **Tasks:** all 15 tasks from the checksum-verified `letta-ai/frontier-memory@v1.0` task release, with the v1.1 corpus used for memory generation. The task IDs are: `apex-brightpath-market-share`, `apex-brightpath-seat-surplus`, `apex-eurogrid-curtailment`, `automationbench-marketing-content-gap-analysis`, `automationbench-sales-chatgpt-proposal-customization`, `automationbench-sales-partnership-contract`, `awilix-release-tier-explicit`, `awilix-release-tier-implicit`, `build-word2vec-pipeline`, `cattrs-compositional-changelog`, `cookie-store-compositional-changelog`, `customer-delivery-contextual-preferences`, `dapt-intrusion-detection-workflow-learning`, `enterpriseops-csm-26d1b04a`, and `enterpriseops-teams-2725d17f`.
- **Corpus:** v1.1, 750 files; manifest SHA-256 `19346a3e46b022ed1def552f8e4f4c50030cefd3250a7a8e10676b46b370b763`. The task release remains v1.0 because that is the pinned public task package. The release/corpus distinction and the dataset-card versus local manifest discrepancy are disclosed in `results/protocol-v4-official.md` and the corpus audit.
- **Model:** `qwen3.8:27b-mtp-q4_K_M` through the local Ollama relay, pinned manifest SHA-256 `22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`; context 262,144; requested effort `max`. Stock Hermes maps its unrecognized model effort to `xhigh`; that behavior is not patched. Local Hermes watchdog limits are extended for the local server as recorded in D100/U1.
- **Harnesses:** official Hermes loader and task agent for A0/HM and Hermes exploratory arms; official Codex and Claude Code adapters for U3 arms, each with only the documented local base-URL adapter and placeholder agent credentials. Claude Code's Messages API compatibility probe must verify both streaming and non-streaming tool use before its gate. If Claude Code requires a translation proxy or request translation, stop and ask the user; do not add one under this preregistration.
- **Runtime and hardware:** Docker runs inside the isolated KVM guest; Ollama runs on bender. Use the same two A30 GPUs and frozen guest/runtime configuration for every arm. Run one task at a time against the single model server. Never use more than two GPUs total. Check that the GPUs are idle before each set; do not stop other users' processes. Stop the guest and serving processes after each set. Keep cluster2 data and logs in the clone or its approved local temporary locations; never use the main study folder or `/scratch`. The runner stops at 145 GiB of study-directory use or below 25 GiB free, before the handoff's 180 GiB hard stop.
- **Judge:** `anthropic/claude-opus-5-5` for APEX tasks, verifier-side only. Agents receive placeholder API keys. The real judge key is passed only to the verifier. If a valid OpenAI judge key becomes available, regrade every saved APEX trial without rerunning agents; report both versions and use the documented OpenAI judge results as primary, as specified by the prior protocol.
- **Concurrency and timeouts:** one trial at a time (`-n 1`), official per-task limits and timeout multiplier 1.0, full limits, no shortened counted trials. The 6-hour memory-generation cap applies to each Hermes generation.

## Planned sets and order

Each counted set contains 3 attempts on each of the 15 tasks (45 trials). A memory treatment uses the exact recorded memory-generation digest. HM1 is reused by the exposure, U3 memory, and delivery arms.

| Order | Arm | Harness and memory condition | Counted trials |
|---:|---|---|---:|
| 1 | A0 | Hermes, no generated memory | 45 |
| 2 | HM1 | Hermes, fresh generation 1 | 45 |
| 3 | HM2 | Hermes, independent fresh generation 2 | 45 |
| 4 | HM3 | Hermes, independent fresh generation 3 | 45 |
| 5 | E-none | Hermes with HM1 memory on disk but no memory block or memory skills index shown at start | 45 |
| 6 | E-all | Hermes with its usual HM1 exposure plus every HM1 memory file injected in sorted path order at start | 45 |
| 7 | C0 | Codex, no generated memory | 45 |
| 8 | CM | Codex, HM1 memory | 45 |
| 9 | K0 | Claude Code, no generated memory | 45 |
| 10 | KM | Claude Code, HM1 memory | 45 |
| 11 | Delivery-cue | Hermes with HM1 cue-triggered skill insertion | 45 |
| 12 | Delivery-scoped | Hermes with the deterministically selected HM1 skills | 45 |
| 13 | Delivery-categorized | Hermes with HM1 skills indexed under fixed categories | 45 |
|  | **Total** | **13 sets** | **585** |

Do not begin counted sets until the full uncounted gate has passed separately for Hermes, Codex, and Claude Code, and the uncounted exposure and delivery Word2Vec preflights have passed. The study driver runs these loader preflights before A0. No interim score-based stopping or arm reordering is allowed. If an infrastructure or safety stop prevents completion, retain and report completed sets and the shortfall; do not substitute runs or change conditions after seeing outcomes.

### Exploratory arm definitions

- **E-none:** disable Hermes memory/profile loading and omit memory skills from Hermes's indexed skills directory; keep the complete memory directory available for tool access. Hermes's bundled skills remain unchanged.
- **E-all:** preserve HM's ordinary memory block and skills index, then add every HM1 memory file's full text, sorted by relative path, through Hermes's supported system-prompt setting. Refuse the arm if the existing 100,000-token estimate cap is exceeded.
- **Delivery-cue:** disable native memory/profile and the memory skills index. For each complete assistant response, tokenize its text and tool calls as case-folded alphanumeric strings of length at least four, excluding the plugin's fixed stop list. A skill activates at most once per trial when any such token overlaps its name or description. If a matching tool-call ID exists, queue the skill for that result; otherwise queue it for the first tool-call ID as fallback. If the response has no tool-call ID, queue it for the next tool result, if one occurs. Activation does not guarantee insertion. The plugin appends queued skill text to the matching tool result. Log counts and digests, not memory text or names.
- **Delivery-scoped:** select memory skills before upload when at least two normalized instruction tokens overlap the skill's declared scope/repository/domain/task metadata; use name/description only if those scope fields provide no evidence. Tokens are case-folded alphanumeric strings of length at least four, excluding the fixed stop-word list in `official/fm_local/delivery_hermes.py`.
- **Delivery-categorized:** upload the HM1 skills and move only HM1 memory-skill entries under the fixed categories User preferences, Environment facts, or Procedural skills using the keyword routing in `official/fm_local/delivery_hermes.py`. Hermes-bundled skill entry text and source-description lines stay byte-identical and appear once; an inventory check fails closed if any entry is changed or duplicated. No skill content or HM1 memory is changed.
- **Delivery-scoped:** when a selected skill has companion files under its skill directory, upload those files with that selected skill; do not upload nested unselected skill directories.
- Exposure-arm instrumentation reads the first model request to count HM1 memory-skill index entries and source headings. It does not rewrite or add content to the request. The same observer is enabled in E-none and E-all.

These are exploratory delivery interventions, not changes to the counted Hermes memory-generation arms. Their exact implementation is pinned by the cluster2 commit recorded before any counted trial.

## Network policy: approved deviation; implementation and validation pending

The D23 model-free probe showed that Harbor 0.24.0's `public` agent policy permits internet egress; `--allow-agent-host 10.0.2.2` does not restrict a public baseline. It reached the relay, both vendor API hosts, and both unrelated probe hosts. The probe used only unauthenticated reachability GETs; no API task request, task trial, or counted trial ran, and no network filter was applied.

**Approved by the user 2026-11-05:** create an isolated cluster2 task copy and set the agent phase to `network_mode = "allowlist"` with `allowed_hosts = ["10.0.2.2"]`, uniformly across task-agent arms. Keep task setup and verifier policies as declared. This limits the task agent's run phase; it does not claim to firewall setup or verifier phases. The launch and audit code must bind the exact copied-task digest and the model-free probe receipt. The probe must show the relay reachable and zero vendor and other hosts reachable. No gate may start until implementation and the setup plan are reviewed; no counted task set may start until the gates pass and the preregistration commit is tagged.

## Outcomes and analysis

- **Primary outcome:** strict pass (`reward >= 1`) under the official scorer.
- **Primary comparison:** pooled HM1–HM3 versus A0. For each task, pool its 9 HM attempts and compare its pass rate with that task's 3 A0 attempts. Use the one-sided exact paired sign-flip test over the 15 task-level differences, alpha 0.05. Report the mean task-level difference, 95% interval from inversion of the same sign-flip test as implemented by the pinned analysis script, task-level differences, and pooled rates with Clopper–Pearson intervals. Those pooled intervals are descriptive only; their independent-trial assumption does not account for clustering by task or memory generation. With 15 tasks, p < .05 may require at least five tasks moving in the same direction and none in the opposite direction. A null result is not evidence of equivalence.
- **Sensitivity analyses for the primary comparison:** exclude the four tasks whose maintainers' reference solutions score zero (`cattrs-compositional-changelog`, `cookie-store-compositional-changelog`, `enterpriseops-csm-26d1b04a`, and `enterpriseops-teams-2725d17f`); and separately exclude trials marked `model_unavailable`. Report the count by arm. The primary result still follows the official reward rule.
- **Exploratory comparisons:** for E-none, E-all, and all three delivery arms, report matched per-task comparisons against HM1 (the same generated memory), as well as comparisons against A0 and pooled HM1–HM3; include the exact one-sided sign-flip p-value and interval for each and label every result exploratory. HM1 is the matched comparator for these loader interventions; pooled HM remains a secondary reference. For CM versus C0 and KM versus K0, report each within-harness memory-effect comparison and its p-value and interval, plus task-level comparisons against A0 and pooled HM1–HM3; the script also reports HM1 as a supplementary reference. Report the script's `model_unavailable` sensitivity comparisons for every exploratory arm. Cross-harness differences and differences between harness-specific memory effects are descriptive only, with no significance tests. Report HM generation-to-generation variation separately.
- **Memory access and exposure:** run `scripts/memory_access.py` for every counted trial. Report whether memory was opened, when it was first opened, and the pinned rule's shown-byte and shown-token estimates, along with the memory digest. For E-all, shown bytes include HM's ordinary `MEMORY.md` block, observed HM1 memory-skill index entries and source headings, plus the separate full-file injection; report each component separately. For U3, contextualize per-trial measurements against the survey's simulated M3 exposure estimates: Codex 10,001 bytes (21%), Claude Code 22,621 bytes (48%), and Hermes 100% of its index. These are reference estimates for M3 under harness loading rules, not expected HM1 measurements; calculate and report actual HM1 values for each trial. Report shown, selected, injected, opened, and model-unavailable counts for exposure and delivery arms. Do not expose memory contents in count-only audit reports.
- **Other secondary measures:** official partial reward, agent time and model tokens where available, and `model_unavailable` by set.
- **No outcome-dependent exclusions:** an attempt with a verifier reward is valid and counts even if the agent times out or crashes. A trial with no reward is an infrastructure failure; repair the cause and rerun that attempt under unchanged settings, without counting the no-reward attempt. If an APEX judge run is incomplete, do not accept the set: regrade its saved output, then rerun the audit and summary validation before continuing. If regrading cannot produce a completed judge result, stop and report the affected set as incomplete. No other exclusions or early stopping are allowed.

## Gates and release conditions

Before any counted set:

1. User approval of the network-policy deviation and preregistration is recorded. The updated policy and audit code are reviewed; the model-free probe confirms exactly the allowed relay host is reachable from the agent phase for Hermes, Codex, and Claude Code.
2. Recheck the clone is on branch `cluster2`, clean, with the approved task-copy digest; confirm the model and corpus digests, reference receipt for all 15 tasks, guest/Docker state, disk headroom, idle GPUs, and that the main study folder and `/scratch` are not used.
3. After approval, commit the approved preregistration and all finalized cluster2 policy, gate, and memory-access validation changes on `cluster2` so the worktree is clean; the gate checker requires a clean worktree. Run full uncounted gates for Hermes, Codex, and Claude Code under the final settings. Each gate must include full memory generation, a memory path, a no-memory path including full-limit `awilix-release-tier-implicit`, customer delivery, one APEX task, serving checks, key audit, summary validation, model route validation, and the corrected relay-only probe. Claude Code's Messages API streaming and non-streaming tool-use probe must pass. The existing Hermes pass receipt was produced under the public policy and does not qualify.
4. After all three gates pass, tag the approved commit `prereg-c2`. The fail-closed checker must validate the tag and three gate receipts. Then run `official/vm/next-study-cluster2.sh`: it validates the tag and gates, then runs and validates five uncounted Word2Vec preflights (E-none, E-all, and the three delivery arms) before A0. These preflights use the validated **Hermes gate generation digest**, not HM1, which does not exist until counted HM1. The study driver validates the preflight receipts; the gate checker itself checks the prereg tag and gates.
5. Start A0 only if every preflight passes. The counted runner must recheck task/memory digests and clean worktree; the HM1 digest from its counted generation is then frozen for the later exposure, U3, and delivery sets.

After each set, validate exactly 45 finished, rewarded trials (3 for every listed task), completed APEX judge status, a consistent memory digest where applicable, key audit, serving check, memory-access output, and the summary validator before continuing. The memory-access validator checks row count, trial/task/reward identity, and memory digest against the scored summary; its receipt binds the archived summary and access-file digests. If a judge is incomplete, regrade and rerun the audit and validation before accepting the set. Archive run-level receipts and update analysis inputs from the set; do not delete source summaries.

## Deviations to report

1. Local Qwen model and relay, as the cluster2 model substitution.
2. Docker runs inside the bender KVM guest; one task at a time and at most two A30 GPUs.
3. Hermes local-server watchdog extensions (U1/D100) and cluster2-specific launch, audit, summary-validation, and fail-closed checks.
4. Cookie-store verifier dependency pin in a separate task copy (D72).
5. Claude Opus 5.5 APEX judge unless/until all APEX records can be regraded with the documented OpenAI judge.
6. U3 Codex/Claude Code harness arms, plus the separate exploratory exposure and delivery arms defined above.
7. Approved task-agent-phase allowlist metadata change from the D23 follow-up; setup and verifier policies remain as declared. Include the exact task-copy digest and measured probe results.
8. Official task release v1.0 paired with corpus v1.1, and the disclosed corpus manifest discrepancy.

## Runtime estimate and stop rules

There are 585 counted trials plus three harness gates, one generation per HM set, and five loader preflights. The handoff estimates the four U3 sets alone at at least four days on the A30s. The full 13-set duration is not established; use the completed uncounted gate timings to update the estimate before counting. On 2026-11-05, the current session measured the cluster2 local directory under `/tmp/fm-c2-$USER` at 104 GiB and `/tmp` with 109 GiB free. The runner's 145 GiB directory limit leaves about 41 GiB of additional growth before its stricter stop; recheck local disk before every gate and set. This sandbox could not see the NVIDIA driver or `/dev/kvm`, so an authenticated host-side hardware recheck is still required before the next GPU gate. Keep the study on the separate cluster2 clone and follow its disk/GPU guards throughout. If the remaining allocation or time cannot complete the plan, report the incomplete design and results as such; do not silently remove arms or compare partial sets as if complete.

## Approval record

- User approval of agent-phase allowlist deviation: **approved 2026-11-05**.
- User approval of this preregistration: **approved 2026-11-05; final policy/audit implementation and gates pending**.
- `prereg-c2` commit/tag: **not created**.
- First counted trial: **not run**.
