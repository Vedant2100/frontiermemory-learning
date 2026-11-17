# Trace pass, run 4 (fm-tasks-run4)

37 failed trials, all opened in `agent/hermes-session.jsonl`, verifier folders and `model.patch`. No trial folder is missing. Every row is in `traces-run4.jsonl`.

## Counts, old against new

Old (layer 1): D1 18, B1 14, A1 3, C6 2. New: A3 14, B1 7, C1 5, A1 3, B3 3, C6 3, C4 2, D1 0. Evidence grade O on 33 rows, I on 4 (the three partnership trials and one marketing trial, where the counterfactual or the corpus side cannot be seen).

## Labels that changed

All 18 D1 rows are resolved. Seven became A3: three Teams trials (call created with only Alice as target, null source, never read back), the CSM trial (a different entitlement was upgraded than the one checked), one marketing trial (email sent with empty recipient and body, then reported as done), and two ChatGPT-proposal trials (one never read the inbox message that overrides the SOP, one accepted a junior rep over the CFO). Five became C1: the two seat-surplus trials, two pcap trials (dapt a1, a2) and one marketing trial. Two became C4 (market-share a2 opened the playbook and skipped mail and chat; ChatGPT-proposal a3 opened it and missed the directive email). Three became B3 (partnership: the agent chose the CRM note over the customer email; memory has no rule for conflicts). One dapt trial became C6.

Seven B1 rows became A3: all three cookie-store trials and four awilix trials. In each, hidden functional tests failed on their own, so no preference lesson could have produced a pass; B1 is kept as a secondary tag. One of them (awilix implicit a2, partial 0.0) is explained: the hidden test file did not compile (TS7006), so zero tests ran. Another (awilix explicit a1) failed the full-suite run on the agent's own timing test, 59 ms against 60. The other seven B1 rows stand (awilix 2, cattrs 2, customer delivery 3): functionality passed and only the unstated preference tests failed, and the memory text has nothing on them. Eurogrid stays A1 (same wrong value in all three attempts, oracle also 0.833).

## What the traces show about memory reaching and being used

The index and the MEMORY block were in the saved system prompt of all 45 trials (checked per trial). The agent opened the skill in 23 of 45 trials, 18 of the 37 failures and 5 of the 8 passes. Memory text turns out to hold task-specific content that the layer 1 pass could not see: the world-server note (paths.md), the pcap metric definitions (contracts.md), and a content-inventory entry (contracts.md). Where that content existed and the agent opened it, it was used: Word2Vec (interface and offline stopword fallback in the written solution) and dapt attempt 3 (every numeric metric right). Where it existed and the agent did not open the one-line index entry ("Playbook for passing verifier-checked agent tasks"), the failures are C1: seat-surplus, dapt a1 and a2, and probably marketing a3. The index description is generic and the pcap definitions sit two hops down (SKILL.md, then references/contracts.md), so B4 is a possible earlier link for those five; I could not separate it from agent habit and kept it as a tag.

## Still unknown

Whether the corpus held the Acme conflict rule, the RetailGiant overrides or the cattrs, awilix and customer preferences: the corpus is not on disk, so B1 versus B3 for those rests on memory text and task-level counts. The marketing a3 and partnership grades are I for that reason. The judge in market-share a2 described a final message that does not match the one in hermes.txt; it does not change that trial's outcome. The Teams call check cannot be read further (database snapshot not retained), so why the call failed beyond the null source is inferred.
