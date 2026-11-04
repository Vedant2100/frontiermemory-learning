# Handoff: memory-harness experiments on a second machine (bender)

Paste everything below the line into a new agent session started on bender (`ssh bender`). Bender's details were checked on 2026-11-04; recheck them before building.

---

You are setting up and running a set of **exploratory memory-harness experiments for FrontierMemory** on **bender**. The main study runs in a Slurm job on another cluster (`crisgc`, node `nodevcggpu02`). **Don't touch it, its files, or its results.** Your study is separate and self-contained.

**Bender shares the home directory with the main study's cluster** (the same NFS mount). The main study runs from `~/frontiermemory-experiment-20261024`, and replacing a file there over NFS has already cut short a running script once. So read the repo there, but never write into it and never run anything from it. Work in your own clone (see *Bender setup*).

## Updates from the main study

Fixes and findings from the main study arrive as numbered entries in `HANDOFF-updates.md` on `main`. **Before every step, run `git fetch origin` and read `git show origin/main:HANDOFF-updates.md`.** Apply each new entry exactly as it says, and log it in your decisions log.

## Context to read first

Read these in your own clone (`~/frontiermemory-cluster2`, branch `cluster2`); the paths are the same.

- `README.md`: the plan, and the questions this study answers.
- `results/protocol-v4-official.md`: the strict setup. Everything is official except the local model. Read it before changing anything.
- `results/preregistration-v2.md`: the main study's design, plus amendment A2 (the relay and the exposure arms).
- `results/decisions-log-detailed.md`, D93–D98: why the main study restarted, and the 15-second proxy cut and its fix.
- `official/fm_local/`: our adapters, all loaded through the official `--harness module:Class` hook:
  - `hermes_local.py`: changes only the model URL.
  - `exposure_hermes.py`: the exposure arms.
  - `model_relay.py`: the relay.
  - `set_tools.py`: set-aside of trials with no reward, and the per-trial summary.
- `official/vm/`: how the main study gets Docker without admin rights (a KVM guest), plus its run scripts:
  - `run-set-v1.sbatch`, `run-exposure.sh`, `next-gate.sh`, `next-study.sh`, `check-serving.py`, `audit-set.py`.
- `scripts/`:
  - `analyze_official.py`: the sign-flip test.
  - `memory_access.py`: shown vs opened.
  - `corpus_coverage.py`, `recency_check.py`.

## Bender setup (checked 2026-11-04)

| | Bender |
|---|---|
| GPUs | 2× NVIDIA A30, 24 GB each (48 GB total, as the main study's 2× RTX 3090) |
| Docker | None. `/dev/kvm` is open to all users, so use the VM route in `official/vm/`. Apptainer is at `/usr/bin/apptainer`. |
| Scheduler | None (no Slurm) |
| CPU and RAM | 40 cores; 251 GB total, about 147 GB available |
| Disk | `/`: 889 GB, 213 GB free. Home (NFS, shared): 3.5 TB free. |

The run scripts were written for the main study's Slurm job. Copy them into your clone and adapt the copies:

1. **Clone:** `git clone "$(git -C ~/frontiermemory-experiment-20261024 remote get-url origin)" ~/frontiermemory-cluster2`, then `git switch -c cluster2`. Get the gated corpus and data the way `README.md` describes, inside the clone, and keep them out of git as the main repo's `.gitignore` does.
2. **Local paths, never on NFS** (the VM disk, the Ollama logs, the build cache): put them under one bender-local directory, for example `/var/tmp/$USER/fm-c2` (check its filesystem and free space first). In your copy of `official/vm/lib.sh`, replace `ROOT=/scratch/$USER/fm-vm`. Build the VM fresh with your copy of the build script; don't copy or open the main study's guest disk.
3. **Run id:** the scripts name logs after `$SLURM_JOB_ID`. Set your own, for example `export SLURM_JOB_ID=c2-$(date +%m%d%H%M)`, once per run, and record it.
4. **Model weights:** `lib.sh` binds the shared models directory into Ollama (see `model_up`). The main study reads the same directory. Bind it read-only (`:ro`), never pull or delete models there, and check the model digest matches `qwen3.8:27b-mtp-q4_K_M`.
5. **Shared tools:** `~/fm-vm-tools` (qemu) and `containers/*.sif` may be read but not changed.
6. **Watcher:** don't run `official/watch.sh` (it watches the main study's Slurm job and keeps its state in `~/.cache/fm-watch`). Write your own with a different state directory, for example `~/.cache/fm-watch-c2`.
7. **GPU check before every set:** replace the Slurm-based steps with an `nvidia-smi` check that both GPUs are free.

## Non-negotiable rules

1. **Official pipeline, except the model:**
   - The `frontier-memory` commands, Harbor 0.24.0, `-e docker`, the official task images, corpus v1.1, 6-hour generation, official task timeouts, effort `max`, `-k 3`, and the official validity rule (a trial with no reward is rerun, never counted).
   - Model: `qwen3.8:27b-mtp-q4_K_M` on Ollama at context 262,144, behind `official/fm_local/model_relay.py`. Without the relay, Harbor's egress proxy cuts slow first bytes at 15 s (D94).
   - Use `-n 1` with one model server.
   - Any other change is a deviation: write it down and ask the user first.
2. **Everything you compare runs on the same hardware, here on bender.** Never compare your arms with the main study's numbers: GPU type (A30 against RTX 3090; the A30 has about the same memory bandwidth but much less compute, so expect slower runs), host and build cache all differ. So you run your own no-memory control and your own default Hermes arm (HM) as baselines.
3. **Freeze the environment:**
   - Validate every task's reference solution against `docs/maintainers.md` first. It should give 10 at 1, Eurogrid about 0.83, and cattrs, cookie store and both EnterpriseOps at 0.
   - Apply the cookie-store `anyio==4.15.1` verifier pin (protocol, D72).
   - Keep one Docker build cache for all arms, with garbage collection off, and never prune it.
4. **Gate before anything counts:** run one uncounted end-to-end set at full settings that includes the longest task (awilix-release-tier-implicit, no memory) to its full limit. It passes only with 0 "client closing the connection" lines and 0 HTTP 5xx in the Ollama log, 0 relay problems (`check-serving.py`), 0 `model_unavailable` trials, and all trials valid. Short-task gates have missed problems twice.
5. **Preregister before running:** write `results/preregistration-cluster2.md` with arms, order, outcomes and analysis, get the user's OK, then commit and tag it (`prereg-c2`) before the first counted trial. Changes after that are dated amendments.
6. **Secrets and data:**
   - Corpus and memory content are gated: never commit, print or quote them. Outputs are counts, digests, ids and paths relative to the memory root.
   - The judge key (Anthropic, the file `~/.config/frontiermemory/anthropic-api-key`; never print it, `cat` it to a terminal, or put it on a command line) goes only to verifiers, via `--ve`, as in `run-set-v1.sbatch`. Agents get a placeholder key. The main study uses the same key, and the user can't set a spend limit. So don't add judge calls beyond the APEX tasks.
   - The repo is public: no personal names, no cluster usernames in committed files.
7. **Shared-machine limits:**
   - At most bender's 2 GPUs. Bender has no scheduler, so before each set check `nvidia-smi`: both GPUs must show under 1 GB used and no processes from other users. If someone else is using them, wait and tell the user. Never stop other users' processes.
   - Keep local disk use under about 150 GB, and stop to prune at 180 GB (`/` had 213 GB free, 77% used).
   - Leave headroom in memory (147 GB available) and CPU (40 cores) for other users.
   - Run long jobs under `tmux` or `nohup` so they survive logouts, and stop the VM and Ollama when idle.
   - Ask the user if unsure, including whether week-long jobs are acceptable on bender.
8. **Records:**
   - Append-only decisions in `results/decisions-log-cluster2.md` (D1…).
   - Commit only your own paths (`git commit -- <paths>`), on branch `cluster2`, never `main`.
   - Don't edit the main study's files. Copy them and give the copy a new name instead.
   - The user sends emails and opens PRs. You draft.

## Arms, in priority order (each 45 trials = 3 attempts × 15 tasks)

All memory arms use Hermes `/learn` memory generated here with the official command, unless an arm says otherwise. The task agent is always Hermes through `LocalHermes` or a subclass of it.

**Baselines, required first:**
- **A0:** no memory.
- **HM:** default Hermes loading, 3 independent generations, as in the main study. If time is short, use 1 generation and state the shortfall.

**Exposure arms**, already built (`exposure_hermes.py`, `run-exposure.sh`, 6 tests in `official/tests/`). They use the first HM generation's memory:
- **E-none:** no memory block and no skills index; files are still openable.
- **E-all:** default loading plus every memory file in full.

Run each first as one uncounted Word2Vec attempt with `E2E=1`. `run-exposure.sh` derives its set script from `run-set-v1.sbatch` by exact string replacements, so copy both together.

**Delivery and organisation arms** (the ideas from our planning discussion). They change the loader only, never the generator, so memory content stays official:
- **Cue-triggered delivery ("System 1/2"):** start like E-none. When the agent's own tool calls or messages match a memory skill's trigger (its name or description terms), inject that skill's text once. Define the matching rule in the preregistration, before any run.
- **Scoped loading:** show only the skills whose scope (repository, domain, task family, as stated in their own metadata) matches the task's repository or instruction. The scope comes from the memory's own text, never from task results.
- **Categorized index:** show the default content regrouped under fixed headings (procedural skills, environment facts, user preferences), with a fixed rule. The bytes are the same as HM; only the organisation changes.

**Generator arms** (a better memory-generation harness). Lower priority. They need their own preregistration section and are clearly labelled non-official:
- A generator built from failures observed in official generation traces, run through the official `--harness` hook.
- It must not be tuned on target-task results. Develop it on a held-out split of the corpus or on pilot data only, and say which.

**Recency:** the source check (`results/recency-check.md`) found nothing to test in the released corpus. A real test means building a perturbed corpus copy, for example by injecting superseded facts with older timestamps. That's a benchmark change: propose it to the user before building it.

## Analysis

- Per arm against A0 and against HM: the same exact one-sided paired sign-flip over tasks as `scripts/analyze_official.py`. Label every comparison exploratory unless the preregistration names a primary one.
- Report per-task pass rates, `scripts/memory_access.py` (shown vs opened) on every trial, the bytes and tokens shown, and the memory digests.
- 15 tasks give low power: p < .05 needs at least 5 tasks moving the same way with none opposing. Don't claim equivalence from a null.

## First steps

1. Do the *Bender setup* below, then read the files above in your clone.
2. Recheck bender: free GPUs, local disk, `/dev/kvm`, and `apptainer exec --fakeroot --nv` working. Load the model at 262k context across both A30s and record the VRAM used. Check the relay with `official/tests/relay-proxy-test.sh` (adapted to your paths).
3. Tell the user the setup plan and the GPU and time budget before building anything.
4. Build the environment, validate the reference solutions, and run the gate.
5. Draft the preregistration and get it approved.
6. Run A0 and HM, then the arms in the order above. Run the audit (`audit-set.py`, `check-serving.py`) after every set, and stop on any serving problem.

Deadline context: the main paper (FORGE) is due Nov 15. These arms feed the follow-up paper (EASE, Jan 22) unless they finish early with clean gates. Report progress to the user at each step, plainly, including failures.
