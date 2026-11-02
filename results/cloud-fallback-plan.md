# Cloud fallback plan (2026-11-01)

Use this only if the GPU cluster becomes unusable. It is decided now so a loss of access costs a day of setup, not a week of choosing.

## Choice: FrontierMemory's native Modal path, with our model served on Modal

```
frontier-memory run-tasks --harness codex -e modal \
  -m openai/qwen3.8:27b-mtp-q4_K_M --allow-host <our-endpoint>.modal.run \
  [--memory <frozen memory dir>]
# env: OPENAI_BASE_URL=https://<our-endpoint>.modal.run/v1, OPENAI_API_KEY=<endpoint token>
```

- **Tasks:** run through FrontierMemory's own runner on Modal, the environment its README uses (`-e modal`). The task containers are the official Docker images and the grading is the official path. That removes our two cluster deviations, Apptainer and the output-path prompt header.
- **Model:** the same Ollama build and model tag (`qwen3.8:27b-mtp-q4_K_M`, 65,536 context) on one Modal **L40S (48 GB)**, the same GPU memory as our 2× RTX 3090, behind an HTTPS endpoint.
  - Codex reaches it through `OPENAI_BASE_URL`. Harbor's Codex agent writes that into Codex's `openai_base_url` (`harbor/agents/installed/codex.py`). Our cluster runs already use Ollama's Responses API (`wire_api = "responses"`), so the protocol is unchanged.
- **Why not a rented VM running our current stack:** that keeps the Apptainer and header deviations. The official Modal route also gives us the setup we need later for the leaderboard work.

## Drift rules (minimal skew)

1. **Never split a task across environments.** A task whose job is interrupted is rerun in full on the new environment (prereg §3), and its cluster trials are reported as lost, not pooled.
2. **Arm comparisons stay within one environment.** Every task reports which environment it ran in. Pooled tests only combine tasks whose three arms all ran in the same environment, or the change is declared and tested as a sensitivity analysis.
3. **Same inputs:** frozen memories and digests, the trial order, k, the model tag and quantization, the context length and the reasoning effort.
4. **Validate before use:** the reference solution must pass and an empty submission must score 0 on Modal for every task (`-a oracle`, `-a nop`), as on the cluster.
5. **Known differences, declared in the paper:**

   | | Cluster | Modal |
   |---|---|---|
   | Runtime | Apptainer | official Docker images |
   | Runner | ours | official |
   | Output-path header | yes | no |
   | Codex version | 0.157 | 0.160.1 (pinned) |
   | Harbor version | 0.24.0 | as pinned |
   | GPU | 2× RTX 3090 | 1× L40S |

   - The Codex memory cap is identical in both versions (2,500 tokens, checked in source).
   - Numerics differ slightly across GPUs.
   - The header difference matters most on Word2Vec, where the path is part of what memory supplies.

## Cost (zero budget)

| Item | Estimate |
|---|---|
| Model GPU, L40S | about $1.95/h ([Modal pricing](https://modal.com/pricing) as reported by trackers; check before use) |
| Remaining work if moved now | about 45 GPU-hours for the matrix + about 20 for A6/A7 ≈ **$125** |
| Task sandboxes (CPU) and grading | small next to the GPU cost |
| Free tier | Modal Starter includes **$30/month**, about 15 L40S hours |

- The free tier covers setup, validation and roughly one task, not the whole rerun. Moving more needs either credits or a decision on paid use.
- The model only runs while trials run. Scale-to-zero means no charge while idle.

## Setup steps (about 1 day)

1. `pip install modal`, `modal token new` (the user's account).
2. Deploy the model server: a Modal app running Ollama on an L40S. Pull the exact tag and keep the model on a Modal Volume so it isn't re-downloaded. Expose `/v1` behind a bearer token. Smoke test one Responses call.
3. Validate the 7 tasks on Modal with the oracle and nop agents. These are CPU only and cheap.
4. Run one A0 Word2Vec trial end to end. Check that the reasoning effort reaches the requests, the prompt hash, and that memory seeding works for one memory arm.
5. Only then queue full tasks, following the drift rules above.

## Not chosen

- **Rented VM** (for example a Lambda A6000 at $0.80/GPU-h, [Lambda pricing](https://lambda.ai/service/gpu-cloud/pricing)) running our Apptainer stack. It is cheaper and is our exact current setup, but it keeps both deviations, is unverified for nested containers, and doesn't help the leaderboard work. Fallback only if Modal can't host the model.
- **Container-based GPU pods** (for example RunPod): Apptainer inside an unprivileged container usually needs user namespaces or seccomp changes ([apptainer#5857](https://github.com/apptainer/singularity/issues/5857)), so it is risky.
- **Academic clusters:** set aside by the user (2026-11-01).

Sources: [Modal pricing](https://modal.com/pricing), [Modal pricing tracker](https://usagepricing.com/blueprint/modal), [Harbor cloud execution docs](https://mintlify.com/harbor-framework/harbor/guides/cloud-execution), [Harbor Singularity PR #1306](https://github.com/harbor-framework/harbor/pull/1306), [Lambda pricing](https://lambda.ai/service/gpu-cloud/pricing), FrontierMemory README (`run-tasks ... -e modal`).
