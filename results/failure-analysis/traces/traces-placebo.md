# Trace pass: placebo arm (fm-tasks-arm-placebo)

All 45 trial folders are present and were opened (agent trajectory, session system prompt, verifier output). 41 failed (reward below 1); the jsonl has one row each. The set-aside serving-fault original (`fm-tasks-arm-placebo.incident-d122/apex-brightpath-seat-surplus__xtGCqZp`) is outside the counted set; I read it only to compare.

## Counts, old and new

| Bucket | Old | New |
|---|---|---|
| A1 | 5 | 5 |
| A3 | 13 | 33 |
| A7 | 3 | 3 |
| D1 | 20 | 0 |

Grades for the new labels: 36 O, 5 I. The five I rows are the A1 rows (three Eurogrid, two cattrs). The verifier side is observed in each, but that the reference solution also scores below 1 comes from TASK-LEVEL.md, which I did not re-check.

## Labels that changed

All 20 D1 rows became A3, each with a specific tag and observed evidence.
- APEX, four trials: three never discovered the world file tools (zero `mcp__world` calls, 6 to 11 steps) and told the user the data was missing; the fourth used plain ARR where the criteria want risk-adjusted ARR. The passing siblings called the world tools at step 5 to 8.
- Marketing, two trials: one missed the newer Slack methodology and followed the superseded email; the other followed the new rule but quoted the old reference code, which a check forbids.
- ChatGPT proposal, three trials: strategy checks fail; one agent found the VP override and still failed two checks, one worked from CRM contacts only.
- Partnership, three trials: all resolved an email-versus-CRM conflict toward $450,000 and Mark Davis, where the checker expects $750,000 and Emily Watson.
- CSM, two trials: entitlement set to 24x7 but no monthly cap (the request gives no cap value); one also left out the premium level.
- Teams, three trials: the call was created with Alice as the only target.
- DAPT, three trials: complete CSV, 8 to 18 of 37 checks differ from the reference (rate buckets, flow definition, traffic flags).

The 13 old A3 rows stay A3 but now rest on verifier lines. Three of the six awilix trials also fail one hidden functional test. Cookie store fails 1 to 8 of 115 functional cases plus the runnable-example gate in all three.

## Memory reaching and being used

The system prompt in every trial holds the MEMORY block (108 of 2,200 characters, a book chapter heading) and a `note-01: Reading notes, part 1.` index line. Exposure was fine in all 45, so B6 does not apply. Failed trials opened the placebo in 4 of 41: Word2Vec trial 2RVBSJN at its first tool turn, SLLSvam at step 5 by listing and step 10 by reading, partnership oYBvtdc at step 33 (called irrelevant at step 34), and cLBLw2t listed the folder only. In two Word2Vec trials the agent treated the novel text as the training corpus ("established text corpus (Moby-Dick notes)" in SLLSvam's code). That is a C5 tag, not a primary bucket, because all three Word2Vec trials fail first on A7: no `/workspace/solution.py`, a path the prompt never names. No failed trial ran near its time limit or hit a model error; all ended `cli_close`.

## What is still unknown

- Why the hidden APEX, Teams, CSM and chatgpt checks fail is read from check names and agent actions, not from check source. For Teams, the exact call shape the check wants is not visible.
- The taxonomy has no code for a memory-free arm on a task that needs a prior fact. Awilix (version 12.1.0, prompt says "tier 7" or nothing) and customer delivery (preference gates) are A3 here only because B1 to B4 are excluded for placebo; a real memory could have helped.
- Whether the placebo text lengthened prompts enough to change behaviour (C7) cannot be shown from a single arm. Control trajectories are needed.
