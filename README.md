# Does memory help coding agents? An audit of the FrontierMemory benchmark

We ran the benchmark's own pipeline with a local open model and asked a simple question: if an agent gets notes distilled from
past runs, does it solve more tasks? **Not by a measurable amount**, and the reasons are as interesting as the answer.
The paper (FORGE 2027, due Nov 15) is drafted in [`paper/`](paper/).

## What the benchmark does

A model reads about 750 past attempts by other agents and writes **memory**: an index file plus a "skill" with 13 reference files
(62 KB in our first run). Then an agent solves 15 held-out tasks (build a Word2Vec text pipeline, learn an intrusion-detection
workflow, write changelogs that meet hidden preference checks, and so on) with that memory available. Hidden tests grade the result.
The public leaderboard ranks systems by how many of 45 attempts pass (15 tasks × 3).

## The result in one table

Passes out of 45 attempts (15 tasks × 3 attempts each):

| Condition | Passes |
|---|---|
| No memory | 6 |
| Memory, run 1 / run 3 / run 4 (three separate generations) | 7 / 4 / 8 |
| **Pooled memory vs no memory** | 19 of 135 vs 6 of 45: **+0.01 per task, p = 0.50** (preregistered test) |
| Placebo: run 1's files with the text replaced by unrelated prose | 4 |
| Read-first: run 1's memory plus "read your memory first" | 8 |

That is no evidence of a gain, and with 15 tasks it is also not proof of no effect.

## Four things we found, with examples

**1. One task benefits, and only from real content.** On the Word2Vec task, the agent without memory wrote code that failed
before any hidden test ran (0% of tests passed, in all 6 attempts, with or without placebo notes). With real memory it passed
72–94% of the tests. Every other task was flat or worse; for instance AutoBench partnership dropped from 51% to 17–25% of hidden
tests passed in every memory condition, **including the placebo**, so showing memory can hurt by itself.

**2. Showing the memory more doesn't help.** We told the agent to read its memory first. It then opened its memory files in 27
of 45 trials instead of 15, and passed 8 instead of 7. Getting the agent to look is not the bottleneck; what the notes say is.
Two more arms point the same way. With every memory file placed in the prompt, the agent passed 7 of 45; with no memory shown at the start (files only on disk), 9 of 45; run 1 had 7. Even on Word2Vec the result barely moved: the agent passed 83–100% of the hidden tests whether or not the memory was shown first.
A third arm gave the agent no generated memory at all, only the past runs related to each task, as files. It passed 9 of 45 (no memory 6), and on Word2Vec it passed all three attempts with 100% of the hidden tests, the best result on that task. For this task, the raw related history was at least as useful as the generated notes.

**3. The leaderboard can't separate the top three.** Ranks 1 to 3 scored 33, 32 and 31 of 45. Rerunning would keep their order about
1 time in 5 (pure guessing: 1 in 6). Our three memory generations of one system passed 7, 4 and 8, which is no more spread than
chance alone. And no no-memory score is published to compare against.

**4. The benchmark loses memory's value at many steps.** Examples:
- For 8 of 15 tasks, no past run in the corpus even resembles the task.
- On 4 of 15 tasks, the benchmark's own reference solution scores 0.
- A failed grader scores the same as a failed agent.
- The benchmark's network proxy cuts a model response that takes more than 15 seconds to start. A slow local model hit that, and the agent gave up and
  was scored as failed (3 of 41 trials in our first control, which we discarded and redid with a fix).
- At the start of a task, one harness shows 21% of the same entry file, another 48%, another 100%.

## Still running

- One more comparison, a better memory writer ("generator"), finishes about Nov 12.
- A second machine is running a quick, separate ALFWorld test of memory methods in an environment where memory has room to help.
  Bar set in advance: at least +15 points over no memory and +10 over hand-written static tips, in at least 4 of 6 task types.

## What's next after the paper

1. For each task, add a short hand-written note built only from what the past runs contain. That measures whether the task needs
   memory at all, and how well the generator extracts what's there.
2. On Word2Vec, remove memory files and single claims one at a time to find what actually helps.
3. Build tasks where memory is needed, goes stale, or is wrong, so memory governance has something to do.

## Where things are

- Paper sources: [`paper/`](paper/). Slides: shared on request.
- Everything we ran, decided and why (job logs, amendments, checks): [`STATUS-DETAILED.md`](STATUS-DETAILED.md) and
  [`results/decisions-log-detailed.md`](results/decisions-log-detailed.md).
- Preregistrations written before any counted trial: [`results/preregistration-v2.md`](results/preregistration-v2.md),
  [`results/preregistration-arms.md`](results/preregistration-arms.md).
- Per-trial data: [`results/official/`](results/official/). Rebuild the anonymous review artifact: `scripts/build_artifact.sh`.
