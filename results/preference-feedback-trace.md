# Why no trial passed a preference check: corpus-side trace (2026-10-31)

Approved as item 2 in D52. This uses the gated v1.0 corpus and our own pipeline outputs only. No verifier, user-preference or solution file was opened. The report gives counts only. Script: `scripts/trace_preference_feedback.py`.

## Question

Every awilix trial failed the user-preference check in all arms (0/30), with or without memory. Could the corpus have taught the preference at all? If it could, did that information survive into the memory, and into the part Codex shows the model?

## Where curated feedback lives in corpus v1.0

- v1.0 contains **35 curated user-feedback messages**, tagged `dreambench-user-feedback-v1` and marked as applying to the preceding attempt. There is one per run, in 35 runs, and **all 35 runs are FAIL**.
- **All 35 are in a single task family**: network-traffic (pcap) statistics, the family closest to our DAPT task. None is in a run related to awilix, cattrs, the cookie store or customer delivery.
- A separate 45 runs (17 topic groups) carry a tagged verifier-result message.
- Runs related to our patch tasks, by keyword in the run's opening text (approximate):

  | Family | Runs | PASS | FAIL |
  |---|---|---|---|
  | awilix / release tier | 6 | 0 | 6 |
  | cookie store | 9 | 3 | 6 |
  | customer delivery | 6 | 5 | 1 |
  | cattrs | 0 | 0 | 0 |

- For the two awilix tiers, the corpus holds **no passing run and no curated feedback**. The preference could only be inferred from failed attempts, if at all.

## Did the feedback survive into memory?

For each feedback message we take up to 8 distinctive terms: tokens found in at most 3% of corpus runs. We then check what share of those terms appears at each stage of the pipeline. 32 of the 35 messages have distinctive terms.

| Stage | Mean share of the message's distinctive terms present | Messages with ≥ 50% present | Messages with none present |
|---|---|---|---|
| Rendered evidence (input to the memory model) | 100% (35/35 messages present verbatim) | 35 | 0 |
| The run's note (stage i) | 62% | 27 | 1 |
| The run's own topic file (stage iii) | 39% | 13 | 5 |
| Anywhere in M3's topic files | 46% | 17 | 3 |
| **M3 injected window (what Codex shows)** | **0%** | **0** | **32** |
| Anywhere in R25's topic files (10 messages in its sample) | 58% | 7 | 0 |
| **R25 injected window** | **0%** | **0** | **10** |

## Reading

1. **On the awilix tasks, the bottleneck is the corpus.** There is no passing run and no feedback to learn the preference from. A 0/30 preference result there says little about memory. We report it as a property of the v1.0 corpus for these tasks.
2. **Where feedback does exist, our pipeline keeps part of it and the harness hides all of it.** The text enters the memory model intact and roughly 40–60% of its distinctive content survives summarisation. None of it reaches the injected window. The agent sees it only if it opens the topic file.
3. **This fits the DAPT and scope-leakage numbers.** On DAPT, the R25 agents opened the pcap topic in 4 of 5 trials and had the best case scores. The M3 agents opened it in 1 of 5 and did worst. Under the frozen name rule (prereg A4), that topic counts as "other-family", because its name shares no word with the task name. The name rule therefore misses the most relevant topic for DAPT. This is a limitation of the preregistered rule and is reported as such.

## Limitations

- Term overlap is a proxy. The memory model may paraphrase feedback, which would undercount survival, and distinctive terms can also come from the attempt itself, which would overcount it.
- Family assignment by keyword is approximate. Runs on related tasks under other names are missed.
- We did not open the tasks' preference files, so we cannot say which corpus feedback, if any, matches a given task's hidden preference.
- Corpus v1.1 drops the tags but keeps similar keyword coverage of these families: release tier 5, awilix 1 and cookie 11 runs by the same rule. This was not analysed further.
