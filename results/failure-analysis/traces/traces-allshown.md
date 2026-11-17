# Trace pass: all-shown arm (exposure-all, job fm-tasks-exposure-all)

All 45 trial folders are present (38 failed, 7 passed); every failed trial was opened. Twin file: `traces-allshown.jsonl` (38 rows). Evidence used: agent/hermes-config.yaml, exposure-report.json, hermes-session.jsonl (messages, reasoning, token anchors), trajectory.json, verifier files, model.patch, and run 1's memory text.

## Counts, old against new
Old (summary level): D1 20, B1 15, A1 3. New: B1 15, A3 6, C6 6, B3 5, A1 3, C5 3. Grades: O 31, I 7 (the I rows are the five apex B3 trials, where "memory is silent" is read but "the corpus could have supplied it" is not checked, and the two partnership C5 trials, where the link from memory text to the choice is inferred). No D1 remains. The 15 B1 and 3 A1 rows keep their bucket and move from I to O, because the verifier output and a grep of the memory now show the missing point directly.

## Did the memory reach the agent
All 13 memory files (62,383 bytes) are in `agent.system_prompt` of hermes-config.yaml in all 45 trials, with 13 end markers. The saved session system prompt does not contain them (it holds the MEMORY.md block and skills index, about 17k characters), so the injection is applied per request and not stored. Two observations show it reached the model: mean prompt per request is 36k to 47k tokens on Word2Vec and Teams against 17k to 25k for the control arm on the same tasks (the gap matches the 16,148-token estimate), and the reasoning in 30 of 38 failed trials quotes a memory file (family names, the t0006 and t0047 trace notes, the git identity). Five more have only a coincidental word match, and three (s84BdKs, CU5R5Jg, RgKW9W9) show no citation (s84BdKs mentions "the analysis family" once at msg 33). No trial opened a memory file with a tool, so access is always "already in the prompt".

## Context window
Last-request prompt size peaks at 189,152 tokens (cattrs Ez5X7vw), below 262,144. Hermes compacted context in two failed trials (awilix implicit qpRX2cM, customer delivery MVaeC3e); the compacted trials still fail only on checks unrelated to compaction. No overflow or truncation text appears in hermes.txt or trial.log. B8 is therefore not assigned to any trial.

## Trials whose label changed, and why
- Apex market share x3 and seat surplus x2 (B3): none of the five opened the mail tool; the passing runs in other arms (run 1, same-arm seat sibling) used mail or the 11-20 meeting note to pick up an exclusion or haircut rule the judge expects. Memory names the Mail app but never says to read mail or notes for clarifications. jpU4d8d did read the notes documents and still missed it, so the rule seems to sit in mail.
- Partnership contract x3: two trials (C5) took the "approval of record governs" reading of the memory and changed the amount and signer; the third (C6) obeyed the "do not silently correct" half, kept the right values, and failed because it never searched Slack, where the process policy lives. Memory holds both rules without saying which wins.
- Word2Vec (C5): the guard advice in memory said nothing about what to return; the agent raised, the two passing siblings returned an empty model.
- DAPT x3 (C6): all three applied the pcap rules and failed the same five assertions: packet-per-minute bucket origin and the port-scan and benign flags. The memory states neither the bucket origin nor a scan threshold.
- Teams x2 (C6): memory warned that the caller's identity is checked; both agents reasoned about it, set no caller, and failed that check.
- A3 x6 (marketing x2, chatgpt proposal x3, CSM): real attempts with named failing assertions; the cause is a wrong source choice, an omitted item, or an unstated requirement. Chatgpt proposal assertions carry no parameters, so the required content is not visible.

## What the traces show about use
Memory was used in most failed trials, and where it was specific (DAPT counts and scoping, Word2Vec path and constants) the agents followed it. Failures sit where it was silent, ambiguous or two-sided. Nothing here shows the long prompt crowding out the memory.

## Still unknown
Whether the corpus runs behind the five B3 trials held the mail rule (not checked). Why CU5R5Jg and RgKW9W9 show no memory citation. What the chatgpt-proposal hidden assertions require. The cause of the two functional-test failures in awilix (RgKW9W9, LKAZKfy) and the extra ones in cattrs Ez5X7vw and customer Pd4aVBK, which are tagged A3 and were not traced.
