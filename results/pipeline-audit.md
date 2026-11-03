# Audit of the official pipeline (working notes, 2026-11-03)

Findings from running the public pipeline. **Holds for any model** unless marked otherwise. Source: official repo at 9af28c2, Harbor 0.24.0, task dataset v1.0, corpus v1.1. Counts only; no corpus or memory text.

## Grader

| Finding | Evidence | Status |
|---|---|---|
| Reference solution scores 0 on 4 of 15 tasks, and 0.83 on one | `docs/maintainers.md` | Reproduced here on all 15 |
| Cattrs and cookie store: the reference passes all tests but not the preference checks, so no reference shows a strict pass is possible | `docs/maintainers.md`; our oracle: cattrs 0, cookie store 115/115 and 1285 tests, reward 0 | Reproduced |
| A failed LLM judge scores as reward 0 and a valid trial, not an infrastructure failure | Our run with a bad key: `status=error, final_score=0.0`, reward 0 on all 3 APEX tasks | Observed; check against official handling |
| Judge identity is not reported. Task files default to Gemini 2.5 Flash, the CLI pins GPT-5.6 Sol | `grading_config.json`, `cli.py` | Read in source |

## Task environments

| Finding | Evidence | Status |
|---|---|---|
| Cookie-store's verifier build doesn't pin `anyio`, while `test.sh` requires 4.15.1 with `--no-index`. Since `anyio` 4.16.0 (2026-11-01), a fresh build writes no reward | Observed; PyPI dates; fixed by one added line (D72) | Reproduced |
| Word2Vec's image installs from a floating GitHub branch, so identical task files build different images | Hashes `888df…` and `b4023…` a day apart | Observed |
| Word2Vec's build took 978–1,069 s here against its own 600 s limit | Our VM; a faster host may fit | Host-dependent |
| Harbor rebuilds images per trial, and 12 of 15 tasks have install commands in their build files, so results can depend on when, and with what cache, a task is built | `docker.py` (`build`, `down --rmi local`); task Dockerfiles counted | Read in source; install commands not checked one by one for pinning |

## Corpus

Script: `scripts/corpus_coverage.py`.

| Finding | Evidence | Status |
|---|---|---|
| Totals match: v1.0 184/490, v1.1 256/494 | Our parser | Verified |
| v1.0 has 9 duplicate files (665 distinct of 674) | Hashes | Verified |
| Runs resembling each task's prompt are very uneven: 8 of 15 tasks have none in either version; DAPT has 35, none passing | `results/corpus-coverage.json` | Approximate: misses same-repo runs with different prompts |

## Submission checks

| Finding | Evidence | Status |
|---|---|---|
| `bundle` records the corpus digest but doesn't compare it to the release, and doesn't check task or attempt counts, though `docs/rules.md` lists these among its checks. Our 1-task, v1.1 bundle reported no problems | `bundle.py`; our run | Observed; the rules also describe a human review |

## Reporting

| Finding | Evidence | Status |
|---|---|---|
| Not published: no-memory rows, per-task results, latency, tokens, memory size, judge | Leaderboard; blog | Read; `docs/rules.md` mentions no-memory rows |
| All 15 published scores are multiples of 1/45, which fits one attempt per task in each of 3 runs; submissions require 3 attempts | Our arithmetic; `docs/rules.md` | Inference |

## Delivery

| Finding | Evidence | Status |
|---|---|---|
| Memory index caps are fixed, independent of the context window | `results/harness-exposure-survey.md` | Read in source |
| Hermes exports memory only at the end of generation, so a timeout leaves none | `hermes_dream.py`; our 20-minute run | Observed |

## Only for our setup (Hermes on local Qwen)

| Finding | Evidence | Status |
|---|---|---|
| Effort: `max` requested, `xhigh` on the wire in 70 of 70 audited requests | Request bodies | Hermes per-model ladders; an unrecognized model tops out at `xhigh` (`agent/reasoning_effort.py`) |
| Generation used 33 minutes of 6 hours and 67 model calls, and gave 8 files, 54 KB | Compliant pass | One run |
| Word2Vec, no memory and memory: 0/3 each in the gate. Memory loaded and the skill was opened; one memory trial reached the right function name with a wrong keyword. Most failures wrote no `/workspace/solution.py`; the official prompt gives no path | Gate trials | Uncounted, 3 attempts each |
| Tool output totalled 290 KB from a 126 MB corpus, about 0.2%. All 750 run IDs appear in output, but only 40 are named in commands | Trajectory counts | One run; scripts may have processed more than they printed |
| 3 HTTP 500s at 15 s each during generation, which recovered | Ollama log | Cause unknown |
