# Trace pass: evidence arm (fm-tasks-arm-evidence)

All 45 trial folders were present. 36 trials failed; each of the 36 was opened (trajectory.json, hermes-session.jsonl, hermes-config.yaml, verifier files). Rows are in `traces-evidence.jsonl`. Counts: 28 grade O, 8 grade P, 0 I, 0 U, 0 D1.

## Counts, old versus new

Old: B2 12, B1 9, A3 11, A1 3, D1 1. New: B2 12, B1 9, A1 3, A3 3, C5 5, C1 2, C4 1, C2 1.

The B2, B1 and A1 rows are unchanged but now rest on trajectories and verifier files, not only on the staging list. Nine rows changed: the one D1 and 8 of the 11 old A3 (the other 3 A3 stay).

## What changed and why

C1, two Teams trials (gmoRCyw, QCKxyFd). Neither ever touched /tmp/hermes/records and both omitted `source` on `create_call`, which is the one failed check (call count 0). The passing sibling SwPJxXW read PASS record t0201, a variant of the task, and its reasoning names that field as the difference. Two staged passing records contain `requestedModalities`. The old label said no staged record could help; that was wrong because the lesson sat in a variant run.

C2, marketing failure (MeJiptm, was D1). It opened failing records t0727 and t0069 and copied t0069's email with the old reference code. Its loop over six records crashed at step 7 before printing the passing ones, and it did not retry. The new code and scores were in the Slack text it read at step 11. The two passing siblings never touched records, so harm from the records is probable (P), not shown.

C5, partnership (3) and DAPT (2). In partnership, the agents mined 15 same-task failing records and sent the contract to the signer those runs chose. In DAPT, XpzA7JA copied flags from failed runs ("previous session judged true"), and 6tQALkq built a consensus across them (port scan true in 23 of 25). Both set has_port_scan wrong. The records held wrong answers, and the agents took them.

C4, DAPT s7EZzRz. It printed the correct feedback ("Do not infer port scanning from the dataset name...") and still set has_port_scan true because the dataset is an attack set. It missed only the two flag checks.

A3 kept (3, AutomationBench proposal). All attempts failed the same two assertions, including EvXqBPx, which opened no same-task record. The 15 staged same-task records all fail. Grade P.

## Whether memory reached the agent

The pointer sits in hermes-config.yaml, not in the session's saved system prompt, so it was seen through behaviour. The 12 trials with nothing staged have no pointer. Of 33 trials with the pointer, 27 ran commands on the records folder: 21 of 24 failures and 6 of 9 passes. Agents searched with grep and parsed files; they rarely read whole records. When a same-task record existed, they mostly used it. The records were helpful in some trials (DAPT values, Brightpath file paths, the Teams pass) and harmful or neutral in others (they carried failing answers).

## Still unknown

Whether the APEX judge's expected values are right (A2 not excluded; the three APEX tasks have no staged record for the task, so memory is out of reach either way). Why the Teams failing attempts skipped the records. The marketing and partnership C5 and C2 labels are P because causation is paired with siblings and control, not observed. The 12 B2 rows fail hidden-preference gates that need a source the corpus lacks.
