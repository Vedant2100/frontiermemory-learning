# Preregistration v2: official setup, local model

**Status: DRAFT, 2026-11-02.** Items marked [smoke] are fixed after the smoke test. Tag `prereg-v2` goes on this file before the first counted trial. Smoke trials are never counted.

Setup: `results/protocol-v4-official.md`. The earlier study is a pilot (`pilot-v1`). It informed this design, and its data are never pooled here.

## Question

With the official public Hermes pipeline and a local open-weights model, does generated memory raise the strict pass rate over no memory on the FrontierMemory tasks?

## Design

- **Arms:** A0, the Hermes task agent with no memory. HM, the same agent with memory from Hermes `/learn` on corpus v1.1.
- **Runs:** HM has 3 independent memory generations, each with 3 attempts on each of the 15 tasks (135 trials). A0 has 3 attempts per task (45 trials).
- **Order:** A0, then HM run 1, run 2, run 3, each with its own fresh generation. Any stopping point leaves complete, reportable sets.
- **Model:** `qwen3.8:27b-mtp-q4_K_M` on Ollama, context [smoke], effort `max`.
- **Generation that fails or times out:** the 6-hour limit stands. If no valid memory results, that is reported, and that run's task trials aren't run.

## Validity

As in the official rules: a trial with a verifier reward is valid, even after an agent timeout or crash, and counts as a failed attempt if it doesn't pass. A trial with no reward is an infrastructure failure and is rerun. No other exclusions.

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
