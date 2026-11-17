# Trace pass: blend arm (fm-tasks-arm-blend)

All 45 trial folders are present; 42 failed (reward below 1) and each was opened (trajectory, saved session prompt, verifier files). Rows are in `traces-blend.jsonl`. Saved prompts were compared with the first user message of the control job's trial for the same task.

## Counts, old versus new

Old: D1 21, B2 9, B1 9, A1 3. New: B1 14, B2 9, B3 6, C4 5, C5 3, A1 3, A3 2. No D1 remains. By grade: O 25 (A1 3, B2 9, B3 6, C4 5, C5 2), P 4 (B1 2, A3 2), I 13 (B1 12, C5 1), U 0. D1 was resolved for market share (2, B1), seat surplus (3, B1), marketing (3: C4 2, A3 1), chatgpt proposal (3, C5), word2vec (3, B3), DAPT (3, B3), CSM (1, A3), Teams (3, C4). The 21 trials that already had B1, B2 or A1 keep those buckets, now with trace support for the arm-structure claims.

## What reached the agent

The blended text was the first user message in 42 of 42 failed trials, identical across attempts of a task, and the system prompt held no memory block or skill index (memory_enabled false). Unchanged-by-design tasks (partnership, awilix explicit, cookie store) carried the original text; arm-report.json shows added_sentences 0. Where text was added, the apex additions were mostly the harness preamble, not a method. Memory could not help the APEX market-share and seat-surplus trials: the needed definitions sit in workspace mail and meeting notes, and the one market-share trial that read them (sibling bD8CbHr) passed with the same blended text.

## What the agents did with it

Used and harmful: the chatgpt-proposal additions say the SOP governs on any conflict. Two agents quote that reasoning when discarding a superseding note (steps 15 and 28), then keep a Competitive Analysis section the grader rejects (C5). Used as written, insufficient: word2vec's guard sentence offers "raise a clear error or return a model"; all three agents raised, and hidden test_case_3 needs a model back (B3). DAPT additions say require evidence for flags, with no thresholds; all three still declared a port scan. Read, not applied: the Teams note that the call must come from the requesting user reached all three agents, but none set create_call's source field, and two final messages say the call was placed from that account (C4). Customer delivery shows the added conventions were followed (repro scripts in 3 of 3 blend trials, 0 of 3 control) without touching the failed preference checks.

## Trials whose label changed, and why

Marketing: two agents named excluded items in the email despite a rule that is in the original prompt and the blended prompt (C4; control passes 2 of 3, so memory added nothing); the third kept the older inbox policy over a newer Slack directive that both siblings adopted (A3, grade P). CSM CSAZHnB set support level enterprise instead of premium; siblings pass (A3, P). Eurogrid stays A1 with stronger proof: the reference run in oracle-all fails the same criterion by 0.01.

## Still unknown

The rewriter input and prompt (blend-instructions.json) are not in the extract, so the origin of added sentences is only matched against run 1's memory text, not shown. B1 labels (12 of 14) rest on corpus coverage, grade I. Whether the 3.8 s mid-trial abort touched any failed trial was not found in hermes.txt or job.log. The zdCGzYF trial uses the blended SOP rule only by inference. Partnership agents changed 750,000 to 450,000 in all three trials; that is the silent correction run 1's memory warns against, but this arm did not carry it.
