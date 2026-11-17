# Run 1 trace pass (set fm-tasks-run1, 38 failed trials)

All 38 failed trial folders were present and opened (trajectory, saved system prompt, verifier output). Memory text was read in full: one skill, `agent-evals/eval-task-families`, a 6.5 KB SKILL.md plus 10 reference files. Rows are in `traces-run1.jsonl`.

## Old versus new buckets

Old: A1 3, B1 15, C6 1, D1 19. New: B1 15, C1 7, B3 6, A3 5, A1 3, C4 1, C5 1. Grades: O 26 (A1 3, B1 15, C1 7, C4 1), P 2, I 10. No D1 remains.

## Labels that changed

The 19 D1 rows resolved as follows. C1 (7): both short seat-surplus attempts and the Teams trio never opened a skill whose reference covers their failure, and two DAPT attempts (3gkqdKh, NLqR7X3) never opened the pcap reference whose rules match 8 of 11 and 7 of 7 of their failed checks. C4 (1): DAPT bbiW8Po opened the pcap reference at step 22, applied its scoping rules, then still flagged a port scan from a distinct-port count. B3 (6): three partnership attempts and marketing 6zkyYb4 followed a memory rule (the policy or approval of record wins) that sent them to the wrong source; chatgpt 2RaQXKA and Zds3nJg never found the SOP and memory does not say where it lives. A3 (5): market share x2 (wrong ARR basis, memory opened early and not at fault), seat-surplus VK7ecQH (23 versus 22), chatgpt mceXiRo (found the SOP, execution misses), CSM (set enterprise rather than premium; siblings passed). The old C6 Word2Vec row became C5: the agent read the empty-vocabulary warning and made the guard return None, which test_case_3 rejects; two siblings with the same memory passed.

B1 and A1 labels stand. Eurogrid shows one criterion (the average value) missed with the same number in all three attempts. For awilix, cattrs, cookie store and customer delivery the preference checks failed and a grep of the memory finds no release, changelog, documentation or delivery rule. Cookie store and two customer rows also carry A3 for failed functional tests.

## Did memory reach the agent, and was it used

The index entry was in the saved system prompt of every trial (38 of 38). Memory was opened in 15 trials, 13 of them failures, matching the earlier count. Opens before the first data read (market share, seat-surplus VK7ecQH, Word2Vec, partnership sfvy7qA, chatgpt Zds3nJg) led to the right environment. Where it helped, it helped by naming the MCP world server; the DAPT scoping rules also took effect when read (bbiW8Po). Where it hurt, it did so through the workflow family text, which turns one failed trace into a rule (follow the approval of record) that matches how four trials went wrong. The description line ("Contracts, paths, commands, failure modes for agent tasks") is generic, and all seven C1 trials skipped the file; I tag B4 on the DAPT and seat-surplus ones but cannot show the description caused the skip.

## Still unknown

Whether the corpus held the facts behind B3 and B1 rows (it is gated and was not read), so B1 versus B3 rests on TASK-LEVEL.md coverage counts. The Teams call failure is inferred from a null call source; the verifier prints no reason. The hidden input of Word2Vec test_case_3 and the packets_per_minute bucketing rule are not in the trial folders. For C1 rows the files show the link broken, not that opening would have fixed the outcome.
