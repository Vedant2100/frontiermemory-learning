# Trace pass: none-shown arm (fm-tasks-exposure-none)

All 45 trial folders are present and all 36 failed trials were opened (session, trajectory, verifier files). Twin file: `traces-noneshown.jsonl`. The pass trials were scanned only for memory contact. The no-reward folder was not needed.

## Was nothing really shown

Yes. In all 45 trials `agent/exposure-report.json` says memory block, skill index and injected bytes are zero (13 files, 62,383 bytes staged, the sha of run 1). The saved system prompt (16,044 chars) has no memory block and no mention of the skill, `memory_enabled` is false in every config, and message 0 is the bare task prompt. The compaction notice in two long runs mentions MEMORY.md, but that is boilerplate, not content.

## How the agent could still find it

The staged folder is `/tmp/hermes/memories` (HERMES_HOME is `/tmp/hermes`). `/root/.hermes/memories` is an empty decoy, so agents that checked the obvious home path found nothing. Across all 45 trials: 4 opened memory content (3 failed, 1 passed), 3 failed trials saw the real folder name in a listing and did not open it, 1 failed trial looked only at the decoy, and 37 never touched it. The 4 openers: two Word2Vec failures and the Word2Vec pass found it because the prompt says "prior implementations of this task" and they grepped for word2vec; one market-share failure found it by grepping for "brightpath". No other route (tool, skill listing, session search) surfaced memory content.

## Old versus new buckets

Old: B7 30, A1 3, D1 3. New: B1 11, A3 9, B7 8, B3 5, A1 3. Grades: O 27, P 6, I 3. No D1 remains.

## Labels that changed

B7 to B1 (11): market share 3, awilix explicit 3, awilix implicit 2, cattrs 1, customer delivery 2. Run 1's memory text has nothing on what was missed (hidden version bump, example and error-context conventions, risk-adjusted basis), so exposure is moot.

B7 to A3 (8): marketing (look-alike audit codes; siblings passed), chatgpt proposal 3 (same two content checks fail in all three), seat surplus 7UxmcVS (data reached, wrong numbers), cookie store 2 and customer delivery bNZ86L8 (functional tests fail on top of preferences). D1 to A3: awilix implicit VrBGMhQ, whose hidden test file failed to compile (TS2339 on `disposer`).

B7 to B3 (3): partnership. Memory touches the exact choice (silent amount corrections) with mixed advice. D1 to B3 (2): Word2Vec xTzHFsx and W5uTWto. These produced `solution.py` from memory (path, signature) and failed test_case_3 because they raised ValueError on an all-stop-word input; memory only says "guard the edge". The pass sibling returned an empty model.

Kept B7 (8): Teams 3 (create_call with Alice only, no caller; memory flags caller identity), DAPT 3 (family-pcap.md rules match the failing tests), seat surplus EfUw679 and Cksn4mn (gave up after the empty local disk and never ran tool_search; memory states the data sits behind MCP tools). A1 eurogrid 3 kept: the same single verifier fails in all three.

## What the traces showed about use

Memory was used correctly where it reached the agent (Word2Vec path and signature, 3 of 3 produced the file; control produced none per TASK-LEVEL), so exploration alone moved Word2Vec from 0 to 1 strict pass. No failure came from time, serving or tooling: exception null in 36 of 36, longest run 76 min.

## Still unknown

Whether the 8 B7 trials would pass with the memory shown (sufficiency unflagged: DAPT and Teams hold partial rules, the seat-surplus numbers also depend on chart reading). The B3 partnership label is grade I. Corpus coverage for B1 comes from TASK-LEVEL.md, not re-derived. Control and run 1 trials were not opened.
