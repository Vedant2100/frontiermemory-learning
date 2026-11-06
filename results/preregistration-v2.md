# Preregistration v2: official setup, local model

**Status: LOCKED, 2026-11-03, tag `prereg-v2`,** before any counted trial. Smoke and gate trials are never counted. Later changes are dated amendments below.

Setup: `results/protocol-v4-official.md`. The earlier study is a pilot (`pilot-v1`). It informed this design, and its data are never pooled here.

## Question

With the official public Hermes pipeline and a local open-weights model, does generated memory raise the strict pass rate over no memory on the FrontierMemory tasks?

## Design

- **Arms:** A0, the Hermes task agent with no memory. HM, the same agent with memory from Hermes `/learn` on corpus v1.1.
- **Runs:** HM has 3 independent memory generations, each with 3 attempts on each of the 15 tasks (135 trials). A0 has 3 attempts per task (45 trials).
- **Order:** A0, then HM run 1, run 2, run 3, each with its own fresh generation. Any stopping point leaves complete, reportable sets.
- **Model:** `qwen3.8:27b-mtp-q4_K_M` on Ollama, context 262,144 (the model's own limit; fits on 2 RTX 3090s), effort requested `max`. Hermes sends `xhigh` for a model it doesn't recognize; this is stock Hermes behaviour, disclosed and not patched.
- **Hardware:** one task-and-arm set stays on one GPU type. Any move is disclosed.
- **Execution:** one allocation runs the sets in the order above, one trial at a time (`official/vm/run-all.sbatch`).
- **Environment:** all arms use one frozen VM disk and Docker build cache, validated by the reference solutions on all 15 tasks, so floating installs in task builds can't differ between arms.
- **Generation that fails or times out:** the 6-hour limit stands. If no valid memory results, that is reported, and that run's task trials aren't run.

## Validity

As in the official rules: a trial with a verifier reward is valid, even after an agent timeout or crash, and counts as a failed attempt if it doesn't pass. A trial with no reward is an infrastructure failure and is rerun. No other exclusions.

A trial whose LLM judge failed (`grading_run_status` other than `completed`) gets reward 0 from the official grader, but it says nothing about the agent. Such trials are regraded from saved outputs with `harbor trials regrade` and the regrade is reported. This is the one place we depart from counting every rewarded trial as it stands.

## Outcomes

- **Primary:** strict pass (`reward >= 1`), via `frontier-memory score`.
- **Secondary:** official partial credit where the verifier reports it; agent time; tokens; whether the memory was opened.
- **Descriptive:** per-task pass rates, run-to-run variation in memory and in score, and the share of each memory shown at start.

## Analysis

- **Test:** one-sided exact paired sign-flip over tasks on the per-task difference in strict pass rate (HM minus A0). HM is pooled over runs within a task. α = 0.05. One primary test, so no multiplicity correction.
- **Effect size:** mean per-task difference with an exact 95% interval from inverting the same test; Clopper-Pearson intervals for pooled rates, which treat trials as independent and are descriptive only.
- **Power, stated in advance:** p < .05 needs at least 5 tasks moving the same way with no task opposing. A null isn't evidence of no effect, and we don't claim equivalence.
- **APEX judge:** the documented judge is `openai/gpt-5.6-sol`. If only a Claude key is available, a Claude judge grades these 3 tasks, disclosed as a deviation, provided it reproduces the maintainers' reference scores (1, 1, about 0.83). If a valid OpenAI key arrives later, every APEX trial is regraded from its saved outputs with `harbor trials regrade`, without rerunning the agent. The official judge's results then become the primary ones, whichever way they move, and both sets are reported. Without any working judge, the 3 tasks are ungraded and the test runs over 12.
- **Tasks with no reference pass:** the maintainers report that the reference solution scores 0 on cattrs, cookie store and both EnterpriseOps tasks. They stay in the primary test, and we report a sensitivity analysis without them.
- **Incomplete runs:** if fewer than 3 runs finish by the go/no-go date, we report what finished and state the shortfall against the official design.

## Scope of claims

Results describe this pipeline with this local model. They don't describe Letta Dream, Letta Code or frontier models. Findings about the benchmark's construction (corpus, graders, reporting, caps) rest on source inspection and hold for any model.

## Amendment A1 (2026-11-03, 22:45, during the control set, before any memory trial)

**Observed:** in 1 of 23 control trials so far, Hermes stopped with "OpenAI API didn't respond in time on any of 3 attempts". The trial got reward 0 and is valid under the official rules. The cause is our single-slot model server: while one long call runs, Hermes's further requests wait and are dropped after 15 s. It isn't the agent failing the task.

**Rule, fixed now, without having seen any memory-arm trial:**
- The primary analysis is unchanged: these trials count as the official rules count them, as valid failed attempts.
- Each trial records `model_unavailable`. We report its count per arm.
- A sensitivity analysis repeats the primary test with those trials excluded.
- No rerun and no change to serving, so all arms keep identical conditions (D85).

**A1 clarification (2026-11-04, 07:50, before any memory trial):** Hermes reports this in two wordings: "didn't respond in time on any of 3 attempts" and "Provider has been unresponsive … for 5 consecutive stale attempts". Both mean it stopped because the model server didn't answer, and both set `model_unavailable`.

## Amendment A2 (2026-11-04, before any counted trial of the restarted study)

**What happened:** Harbor's egress proxy cuts a model response whose first byte takes over 15 s (D94). Cloud APIs answer sooner; our local model sometimes didn't, so the first control ran under conditions that official runs never see: 420 cut requests and 3 of 41 trials given up.

**Changes, fixed now:**
- **The first control is discarded.** It is reported as pilot data (job folder `fm-tasks-control-pilot2`) and never pooled.
- **A relay is added** in front of the model server (D95). It passes fast responses through unchanged and keeps slow ones alive so the proxy doesn't cut them. Model output is untouched.
- **Restart in the original order:** control, then runs 1–3, as in the design above, after an uncounted gate at full settings with the relay. The gate includes the longest task (awilix, no memory) run to its full limit, a memory task and an APEX task, and must show 0 cut requests and 0 `model_unavailable` trials.
- **A1 stays as a safeguard:** `model_unavailable` is still recorded per trial, with its sensitivity analysis. We expect 0 such trials.

**Exploratory exposure arms (not part of the primary test).** After run 3, two further sets of 45 trials (3 attempts × 15 tasks) use run 1's memory (`fm-gen-run1`) with the HM task agent. Only what memory is placed in context at start changes:
- **None shown:** no memory block and no memory-skills index. Every memory file stays on disk and can be opened with tools.
- **All shown:** HM's loading, plus the full text of every memory file, injected through Hermes's `agent.system_prompt` setting in sorted path order. It is refused above 100,000 estimated tokens.

The order is none shown, then all shown. Model, relay, timeouts, one trial at a time, judge and validity rules are the same as HM. Each arm is first checked end to end on one uncounted Word2Vec attempt. Results are reported descriptively per task against HM run 1 and the control, with the same sign-flip statistic labelled exploratory. Each trial logs the memory digest and the shown and injected byte and token counts. If time runs out, an unfinished arm is reported as such.


## Amendment A3 (2026-11-04, before any counted trial of the restarted study)

The first restart gate (job 305865) failed: customer delivery with memory ended `model_unavailable` ("unresponsive for 5 consecutive stale attempts"). At effort `max`, Hermes cancels a model call after 300 s without a stream event and gives up after 5 such calls in a row. The cancels didn't stop the model, so each retry queued behind the abandoned calls (waits 155, 322, 565 s). One pilot cookie-store trial gave up the same way. Two changes, both in our serving layer and adapter, with no change to Hermes's code, the tasks, the model or the effort:

1. **Watchdog settings** (`official/fm_local/hermes_local.py`): `HERMES_CODEX_TTFB_TIMEOUT_SECONDS=900` and `HERMES_CODEX_EVENT_STALE_TIMEOUT_SECONDS=900` (what Hermes gives local servers for the first event), and `HERMES_API_CALL_STALE_TIMEOUT=1800` (Hermes's own per-call socket timeout). They apply to the task agent and the generator. This is a disclosed deviation from default Hermes settings, made for local serving only.
2. **Retry supersede in the relay** (`official/fm_local/model_relay.py`): a POST byte-identical to one still in flight cancels the older call at Ollama.

The serving check counts Ollama aborts caused by these cancels as expected, and still fails any other abort. A second gate (`official/vm/next-gate-2.sh`: a fresh generation, customer delivery and APEX with that memory, then awilix with no memory to its full limit) must pass before the control starts. Everything else in A2 is unchanged, including the order, the `model_unavailable` flag and the sensitivity analysis. The first gate is reported as an uncounted infrastructure check.


## Amendment A4 (2026-11-06 01:30, after run 2's generation failed and before any run 3 task result)

**What happened:** run 2's memory generation reached the official 6-hour limit (`AgentTimeoutError`) and exported no memory. As line 20 above says, this is reported and run 2's trials weren't run (D113). The likely cause is serving capacity: the generator delegated to parallel sub-agents, our single model slot serialised them, and the median wait for a model reply was 596 s.

**Change (user decision, Nov 6):** one replacement memory run, **run 4**, is added after run 3 and before the exploratory exposure arms. Its procedure is identical: a fresh generation under the same 6-hour limit, then 3 attempts per task with the HM task agent, the same settings, checks and validity rules. If run 4's generation also fails, that is reported the same way, with no further replacement.

**Analysis:**
- **Primary:** unchanged in form. HM pools every memory run that produced valid memory: runs 1, 3 and 4, or fewer if a generation fails.
- **Sensitivity:** the same test without run 4, i.e. the runs preregistered in the original design.
- **Reported in full:** run 2's failed generation, with its duration, call count and wait times.


## Amendment A5 (2026-11-06, before any exposure-arm trial)

**Change (user decision, Nov 6):** the two exploratory exposure arms are reordered and nothing is dropped. **All shown** runs right after run 4, as the last set of this study's job. **None shown** moves into the exploratory arms' order (`results/preregistration-arms.md`), after the placebo and read-first arms and just before the cue-triggered arm, whose comparison it serves.

**Why:** all shown tests a finding already in the paper: Hermes shows 1 of 13 memory files at start (D106). None shown matters most as the control for cue-triggered delivery. This order gets the results most relevant to the paper sooner.

**Unchanged:** both arms' designs, checks, analysis and exploratory status (A2). Run 4 (A4) still comes first. The primary test is not affected.
