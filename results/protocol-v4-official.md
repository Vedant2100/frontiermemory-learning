# Protocol v4: official setup, local model (2026-11-02)

Requirement: conform to official runs in everything except that the model is local. Any change not listed under "Allowed differences" is a deviation and goes to the user first.

## Checklist

| Item | Setting | Source | Verified |
|---|---|---|---|
| Repo | `letta-ai/frontiermemory` HEAD (9af28c2), Harbor 0.24.0 | README | ☐ |
| Python | 3.12+ with uv | README | ☐ |
| Commands | `frontier-memory generate-memory`, `run-tasks`, `score`, `bundle`, unmodified | README | ☐ |
| Runtime | `-e docker`, official task images | README, `cli.py` | ☐ |
| Network | Declared `no-network` kept; generation reaches only the model host | `docs/rules.md` | ☐ |
| Generator | `--harness hermes` (`/learn`, ref `d923a5eb`), one fresh memory per run | `agents/hermes.py`, `hermes_dream.py` | ☐ |
| Task agent | `--harness hermes`, native memory loading | `agents/hermes.py` | ☐ |
| Tasks | All 15 in `letta-ai/frontier-memory@v1.0` | `cli.py` | ☐ |
| Attempts | 3 per task (`-k 3`) in each of 3 runs: 135 trials | `docs/rules.md` | ☐ |
| Control | Same agent, no memory, 3 attempts per task: 45 trials | README | ☐ |
| Limits | 6-hour generation; official task timeouts; multiplier 1.0 | `docs/rules.md` | ☐ |
| Effort | `max` for generation and tasks, as the leaderboard states; confirm it reaches model calls | leaderboard, `docs/rules.md` | ☐ |
| Web tools | Off, as the Hermes adapter sets them | `hermes_dream.py` | ☐ |
| Grader | Unmodified verifiers. APEX uses `openai/gpt-5.6-sol` | `cli.py` | ☐ needs an API key |
| Infrastructure failures | Trials with no reward are rerun and not counted as failures | `docs/rules.md` | ☐ |

## Corpus

v1.1 (750 runs). The leaderboard labels its tables v1.1, while the public code pins v1.0, with v1.0's digest in `corpus.py` and its bundle check. We disclose this. We also disclose the v1.1 digest mismatch recorded in `results/corpus-v1.1-audit.md`: the dataset card gives `47641d5b…` and the files hash to `19346a3e…`.

## Allowed differences, all from the local model

| Difference | Why | How it's kept minimal |
|---|---|---|
| Model is Qwen3.8-27B on Ollama | The study's one permitted change | Same model for generation and tasks, as the blog does per harness |
| Base URL points at our server | The Hermes adapters hard-code the OpenAI and Anthropic URLs | Thin subclass through the official `--harness module:Class` hook; nothing else overridden |
| Context size | Set by GPU memory | Largest that fits, found in the smoke test and recorded. No compaction setting of ours |
| API key value | A local server needs none | Placeholder value |
| Judge key reaches only the verifier | No spend limit is available, and the task files would otherwise expose the key to the agent | Host `OPENAI_API_KEY` is the placeholder, so agent containers get that. The real key goes through Harbor's verifier-only `--ve`, as `GRADING_MODEL` already does. Grading is unchanged |

## Host setup (not part of the protocol)

The cluster has no Docker. Real Docker Engine runs in a KVM guest inside a Slurm job, and the harness runs `-e docker` in that guest. Ollama runs on the host with the GPUs, reached at `10.0.2.2`. This is our way of providing a Docker host, like any machine would; the guest kernel is the only thing specific to it. We record the versions of the guest OS and Docker.

## Validation, before any counted trial

1. VM boots, `docker run hello-world` works, and outbound access works.
2. The official network probe shows the model host reachable and others blocked.
3. Oracle on all 15 tasks matches the maintainers' list (`docs/maintainers.md`): 10 score 1, Eurogrid about 0.83, cattrs, cookie store and both EnterpriseOps score 0.
4. **End-to-end gate on one small task (Word2Vec). No full run starts until every check passes.** Nothing from this gate is counted.
   - **Plumbing pass:** a short generation time limit, to catch failures cheaply. Qwen must drive Hermes tools, and effort must reach the model.
   - **Compliant pass, with nothing changed from the full-run settings:** `generate-memory` on the full corpus under the real 6-hour limit, then `check-memory`, then `run-tasks` on Word2Vec with that memory and with no memory, then `score` and `bundle`.
   - **APEX judge check:** one APEX grading confirms the judge still calls OpenAI, while the agent's base-URL override reaches only the agent. Inspecting the agent container confirms it holds only the placeholder key, and trial logs show no use of the real one.
   - **Checks:** the commands are unmodified; during generation only the model host is reachable; logs show the memory loaded (memory trial), absent (control), the same digest, and the requested effort; the verifier wrote a reward; a diff against upstream shows only the base-URL subclass. `bundle` will report the 14 tasks not run; any other problem must be explained.

## After each run

`frontier-memory check-memory`, `score`, `bundle`. Bundle problems must be empty apart from the disclosed v1.1 digest.

## Shared-cluster limits

This is a shared cluster. They apply to every job and are not part of the comparison.

- **GPUs:** never more than 2 in total at any moment, across all our jobs. Every GPU job uses `--job-name=fm-serial --dependency=singleton`, so GPU jobs run one at a time. Two single-GPU model servers count as 2, and only in place of the 2-GPU job.
- **CPU and memory:** request what the job needs and scale to its concurrency: about 2 CPUs and 8 GB per concurrent task, plus the VM's overhead. Release the allocation when idle; no VM stays up between jobs.
- **Disk on `/scratch` (local to `nodevcggpu01`, shared):** the guest disk is sparse. Check its real size at each step. Investigate at 250 GB and stop to prune at 350 GB. Remove the guest's unused Docker images, build caches and failed trial data once archived.
- **Home (NFS, hit its quota on Nov 1, D56):** only scripts, small tools and summaries. Trial workspaces stay in the guest; copy back only what the paper needs.
