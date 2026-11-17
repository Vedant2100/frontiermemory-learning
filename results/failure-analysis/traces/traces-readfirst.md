# Trace pass: read-first arm (fm-tasks-arm-readfirst)

All 37 failed trials were opened (trajectory, verifier output, session record). No trial folder is missing. Memory text is run 1's: one skill, eval-task-families, with a 6.5 KB SKILL.md and 11 reference files. Rows are in `traces-readfirst.jsonl`.

## Old versus new buckets

Old: B1 11, A1 3, D1 23. New: B1 14, A3 8, C1 5, A1 3, B3d 3, C6 3, A7 1, D1 0. Grades: O 22, I 12, P 3. All 11 old B1 and 3 old A1 labels stand. All 23 D1 trials are now assigned. Time, serving and exception causes (A5, A6, A4) are excluded for all 37: no exception, no timeout in `result.json`, and the longest run is 103 steps.

## Labels that changed and why

- B1 (3 new, was D1): awilix P6zn8RP (hidden suite did not compile; version-bump preference also failed), cookie h5ZQsAn and qqwASgX (runnable-docs-example gate failed, plus hidden test failures). The preference conventions appear nowhere in the memory text (grep) and the corpus has 0 to 1 related runs. Functional misses are kept as an A3 tag.
- A3 (8): market share x3 (the rubric wants churn-risk-adjusted ARR, which the prompt never states; the three related corpus runs show only the column name), chatgpt proposal x3 (strategy-content assertions the memory does not cover), cookie 4tWQuo3 (empty-valued cookies; preference passed), CSM joBDTwD (picked entitlement 29, siblings that passed changed 31).
- C1 (5): seat surplus 9qboL5t and Sg6FRMq searched the empty local disk and answered that the files were missing after 4 tool calls. The analysis reference says the data sits behind the world MCP server. A sibling that opened it at step 5 reached the data (grade P). Teams x3 never opened memory and created the call with only Alice as target; the office reference names caller identity as a checked failure mode but gives no fix (grade I).
- B3d (3): partnership. All three opened the workflow reference early, then set the amount to $450,000 and signed to Mark Davis, as the reference describes. The verifier wants the $750,000 subject and Emily Watson. No reasoning text is saved, so use of the memory is inferred from timing and wording.
- C6 (3): DAPT. The agents read the pcap reference first and applied its evidence-based flag rules, and still wrote has_port_scan true and is_traffic_benign false (expected false and true). The reference gives no threshold, and the 35 related corpus runs have no pass.
- A7 (1): seat surplus QVfNmrb opened memory at step 5 and answered at step 41, but a second user-role turn at step 42 became the final reply. Its step 41 numbers were also wrong.

## Did the nudge reach the model

Not shown by the saved prompt. In all 45 trials the saved system prompt (`hermes-session.jsonl`, line 1) contains the MEMORY.md block and the skill index, and none contains the nudge sentence. The nudge is in `hermes-config.yaml` (identical file in all 45) and `arm-report.json` carries a digest that equals the SHA-256 of the sentence (I recomputed it). The decision log (D126, D128) says Hermes appends that key at request time, so absence from the saved prompt is expected; the request itself is not in the trial files. Behavior is consistent with delivery: 27 of 45 trials opened memory, 13 at the first assistant turn. That is support, not proof.

## What the traces showed about use

Opening mattered when the trial had no other way in: the seat-surplus pair that did not open gave up, the one that did found the files. In 14 of 37 failures (awilix, cattrs, customer delivery, cookie) the memory held nothing relevant, so opening or not made no difference. The partnership memory was applied and hurt. Of 14 never-opened failures, 5 are C1; the other 9 are B1 or A3 with nothing in memory to find.

## Still unknown

Whether the model's first request carried the nudge (needs the model-server log, not in the trial folders). Why the step 42 turn appeared in QVfNmrb. Whether the CSM and chatgpt A3 labels hide a missing generic rule; the rubric text for those tasks is not in the retained files beyond check names. The C1 grade for Teams rests on inference about which parameter the checker reads.
