# Trace-level pass: brief for arm agents

Goal: redo the failure classification of one arm using the raw trial data that is now available, and replace
every D1 (undeterminable) and A3 (residual) label with an observed one wherever the data allows.

## Data (read-only)

Root: `<extract dir>/data/home/fm/official/frontiermemory/jobs/`

Each arm is one job folder holding 45 trial folders named `<task>__<id>`. The trial id in the arm's
`arm-<arm>.jsonl` is the folder name. Inside a trial folder:

- `agent/trajectory.json`, `agent/hermes-session.jsonl`, `agent/hermes.txt`, `agent/hermes-config.yaml`
- `verifier/reward.txt`, `verifier/test-stdout.txt`, `verifier/*ctrf.json`, `verifier/functional-reward.txt`
- `result.json`, `config.json`, `trial.log`, `artifacts/logs/artifacts/model.patch`

Memory text for run 1/3/4 and the generator runs: `jobs/fm-gen-run{1,3,4}/memory-task-v1.1__*/artifacts/memory/`
(`MEMORY.md`, `skills/**/SKILL.md`, `references/`). Placebo, blend and evidence arms have their own staged files,
inside their trials' `agent/` folders or job folders; look before assuming.

Do not write to or move anything under that root. Do not run git. Write only to
`results/failure-analysis/traces/`.

## Method

Read `TAXONOMY.md` (same folder) first: bucket codes, the serial questions, the evidence grades O/P/I/U.
Read `arm-<arm>.md` and `arm-<arm>.jsonl` for the earlier, summary-level labels of your arm.

For every failed trial of your arm (reward < 1 in the jsonl), look at the trajectory and answer in order:

1. Could any memory have changed the outcome (task fully solvable from the corpus/oracle, judge, verifier)?
2. Did memory contain the needed content (check the arm's actual memory text)?
3. Did it reach the agent: was it in the system prompt/first message, was the index shown, did the agent open files
   (which, at which turn)? Check the saved prompt in the session/trajectory, not only the config.
4. Did the agent apply it correctly?
5. If memory is not the cause: what is? (ran out of time, context overflow, serving error, tool failure, wrong
   deliverable, verifier/judge failure, task never solvable.) Cite the file and turn or line.

Then assign one primary bucket (earliest broken link, TAXONOMY.md rules) plus secondary tags, and an evidence grade.
Use O only when you read it in the files. Keep U only where the files really do not show it, and say what is missing.

## Output

Write two files per arm into `traces/`:

- `traces-<arm>.jsonl`: one row per failed trial with fields arm, trial, task, attempt, reward, old_bucket,
  new_primary_bucket, secondary_tags, evidence_grade, evidence (list of short strings with file and turn
  references), and one sentence on what happened.
- `traces-<arm>.md`: at most one page. Counts of old versus new buckets, the trials whose label changed and why,
  what the traces showed about memory reaching and being used, and what is still unknown. Plain prose, labels as
  headers, no verdict-style headings.

Rules: the corpus is gated and the traces contain task material. Quote at most 25 words from any file, and only
when needed as evidence. Do not claim anything about a trial you did not open. If a trial folder is missing,
say so. Keep your final reply to the parent under 150 words: counts per new bucket and the single most
important finding.
