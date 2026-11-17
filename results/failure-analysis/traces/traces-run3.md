# Run 3 trace pass (fm-tasks-run3, 41 failed trials, all 41 folders present)

Source: trial folders (hermes-session.jsonl, trajectory.json, verifier files, calls.jsonl, model.patch) and the run 3 memory text (one skill, task-contract-playbook, 4 references, about 40 KB). Per-trial rows are in traces-run3.jsonl. Message numbers are indices into hermes-session.jsonl.

## Counts, old and new

| Bucket | Old (layer 1) | New | New grades |
|---|---|---|---|
| A1 | 3 | 3 | O 3 |
| A3 | 2 | 15 | O 14, I 1 |
| B1 | 12 | 14 | O 14 |
| B3 | 0 | 6 | I 3, P 3 |
| B4 | 0 | 3 | P 3 |
| D1 | 24 | 0 | |

## Labels that changed

All 24 D1 trials are now assigned. Market-share (3) and seat-surplus (3) split three ways. Market-share attempts 2 and 3 and seat-surplus attempt 1 are B1: the agent had the data and used the wrong basis (unadjusted ARR or customer counts, ignoring Churn_Risk_Flag; a different target basis). Market-share attempt 1 and seat-surplus attempts 2 and 3 are B4: the agent searched the empty filesystem, concluded the data was missing, and never used the world MCP tools. Sibling attempts with the same memory found those tools. Marketing (2), chatgpt-proposal (3), partnership (3), word2vec (1) and dapt (3) are A3, each with an observed cause (404 on the Slack history call, older email chosen over a later Slack message, override email unread or read and not applied, 450k and Mark Davis chosen over the 750k and Emily Watson the verifier encodes, stopwords keyword forwarded into Word2Vec, IPv6 and bidirectional-flow conventions). CSM (3) and Teams (3) are B3. Cookie store attempt 1 moved from B1 to A3: it has a stray committed file `test` (a gate the playbook covers) but also four failing hidden tests, so fixing the gate alone could not give a strict pass.

CSM: all three miss the check for premium, 24x7 and a monthly cap. Attempt 1 repeats the FM-3 pattern (wrong entitlement, deactivated the right one); attempts 2 and 3 edit entitlement 31 but set level enterprise with no cap. The memory names this task but records no final values. Teams: all three create_call requests omit `source`; a passing call in the evidence arm includes it and also ends in state establishing. The playbook's FM-7 blames the state, which is the wrong lesson (B3d).

Unchanged: A1 eurogrid (the reference answer 243,275.56 also scores 0.83; agents reported 228,025.94), 12 B1 trials, now with the verifier reason read (version bump 12.1.0, runnable example, structured error context, async example). Awilix implicit attempt 1 "tests zero" is a hidden test file that fails to compile (`.disposer` missing), a functional failure and not an environment fault.

## Memory reaching and being used

The MEMORY.md line and the skills index entry were in the saved system prompt of all 41 trials. Only 11 trials opened the skill (market-share 2 and 3, eurogrid 2, chatgpt 3, partnership 1 to 3, awilix implicit 2, word2vec, cattrs 1, customer-delivery 1). None of those 11 changed because of it; the word2vec trial used the path and function name correctly and failed on a keyword bug, and two siblings passed. In the other 30 the index description ("Decode task contracts, paths, protocols, failure modes.") did not prompt an open, and the Hermes prompt tells the agent to load skills only for knowledge it lacks. Six trials hit a point the memory states: the empty-container rule (three), FM-3 (CSM attempts 1 and 3), the clean-tree rule (cookie 1). The memory gave nothing usable for the other 35. The Teams lesson is wrong, not absent.

## Still unknown

Whether opening the playbook would have fixed the three B4 and the CSM attempt 1 trials is inferred from siblings and the text, not observed. B3 on CSM is grade I because the source runs are not on this host, so whether the PASS runs held the values the memory dropped is unchecked. The partnership, chatgpt and marketing verifiers are heuristic checks whose bodies are not in the files; the last miss in chatgpt attempt 3 (strategy_partnership) is grade I. The A2 judge question for the APEX tasks is untouched: the judge rationales read consistently with the answers, but no separation test was run.
