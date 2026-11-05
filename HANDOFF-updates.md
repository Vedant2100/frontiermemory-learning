# Updates for the bender study (cluster2)

Append-only: the main study adds a numbered entry here whenever a fix or finding applies to you. **Check this file before every step** (`git fetch origin && git show origin/main:HANDOFF-updates.md`) and apply every entry you haven't applied yet, in order.

For each entry:

1. Bring in the listed files from the listed `main` commit, on your `cluster2` branch: `git checkout <commit> -- <files>`. These files hold no machine-specific paths, so copy them as they are. If you adapted one of them, merge the change into your copy by hand and say so.
2. Run the listed check.
3. Write a line in `results/decisions-log-cluster2.md`: "Applied U<n> (main `<commit>`)", what you checked, and the result.
4. Commit only those paths on `cluster2`.

If an entry changes how trials run, every counted trial must come after it. Trials run before it are uncounted or need a dated amendment: say which, and ask the user. Never push to `main`. If something here conflicts with what you see on bender, stop and report it to the user rather than guessing.

---

## U1 (2026-11-04): Hermes watchdog limits, relay retry supersede, serving-check fixes

**Why:** the main study's first restart gate failed (decision log D99, D100; prereg-v2 amendment A3).
- At effort `max`, Hermes cancels a Responses call after **300 s without a stream event** and gives up after 5 such cancels in a row. The trial ends `model_unavailable` ("unresponsive for 5 consecutive stale attempts").
- The cancel doesn't stop the model behind the egress proxy, so each retry queues behind the abandoned call.
- A local 27B model on a long prompt hits this; customer delivery with memory did. Your A30s are slower than our 3090s, so expect it more often.
- Separately, Hermes cuts its post-turn background-review call when the agent exits. The relay logs that as a client close, and the old serving check wrongly failed it.

**Main commits:** `e097c2c` (D99) and `c878b96` (D100). Take the files from `c878b96`:

| File | Change |
|---|---|
| `official/fm_local/hermes_local.py` | `WATCHDOGS`: `HERMES_CODEX_TTFB_TIMEOUT_SECONDS=900`, `HERMES_CODEX_EVENT_STALE_TIMEOUT_SECONDS=900`, `HERMES_API_CALL_STALE_TIMEOUT=1800`, set on every task-agent and generator command |
| `official/fm_local/model_relay.py` | A POST byte-identical to one still in flight cancels the older call at Ollama. New log fields: `body_sha`, `superseded`, `supersedes` |
| `official/vm/check-serving.py` | Excuses a client close only when it is within 2 s before to 10 s after an agent's finish. Excuses Ollama aborts up to the number of superseded calls. Reads `results/official/summary-*.jsonl`, so if your summaries live elsewhere, pass `--summaries <dir>` |
| `official/tests/test_hermes_local.py` | New tests for the above |
| `official/vm/next-gate-2.sh` | The main study's second gate, for reference: same parts and checks as `next-gate.sh` |

**Check:**
- `.venv/bin/python -m pytest -q official/tests`: all pass, including the 4 in `test_hermes_local.py`.
- Your gate must include **customer-delivery-contextual-preferences with memory**, as well as awilix with no memory to its full limit, and pass `check-serving.py`.
- In your relay log, look at any call with `superseded` and at the `body_sha` of retries. Report whether retries carry identical bodies: the main study hasn't confirmed that yet.

**Effect on your study:** this changes how trials run. Apply it before your gate and before any counted trial. Your preregistration should list these settings as disclosed deviations, as A3 does.

## U2 (2026-11-04): main-study gate 2 passed with U1's fixes

No new code. With U1 applied, the main study's gate 2 passed: customer delivery with memory and awilix with no memory both finished valid with no `model_unavailable`. The Ollama log had 0 client aborts, and the relay had 0 upstream errors and 1 client close excused at an agent's end. One call ran 415 s and finished, so the 1800 s per-call timeout is what fixed it. No retries happened, so whether retries are byte-identical is still open. Report it if your relay log shows any `superseded` call.

**Effect on your study:** none beyond U1. Gate 1's results without U1 are not representative, so don't treat them as a baseline.

## U3 (2026-11-04): new arms, harness comparison (Codex and Claude Code), user decision

The user added a harness comparison to your study. Like everything on bender, it is exploratory. It changes **only the task agent**. The memory stays the same: your first HM generation, the one the exposure arms use, with the same digest.

**Arms** (each 45 trials = 3 attempts × 15 tasks, all on bender):

| Arm | Task agent | Memory |
|---|---|---|
| C0 | Codex | none (the adapter still turns its memory feature on, as the official code does) |
| CM | Codex | HM generation 1 |
| K0 | Claude Code | none |
| KM | Claude Code | HM generation 1 |

**Order:** A0 and HM, then E-none and E-all, **then C0, CM, K0 and KM**, then the delivery arms (cue-triggered, scoped, categorized), then the generator arms. Update your preregistration draft to match before you ask the user to approve it.

**Adapters:** use the official ones through the `--harness` hook:
- `frontier_memory.agents.codex:MemoryCodex`
- `frontier_memory.agents.claude_code:MemoryClaudeCode`

Keep the CLI versions pinned in `frontier_memory/agents/__init__.py` (`DEFAULT_CLI_VERSIONS`: Codex 0.160.1, Claude Code 2.1.284). Write one subclass of each in new files, `fm_local/codex_local.py` and `fm_local/claude_code_local.py`, the way `hermes_local.py` subclasses Hermes. The subclass may change only the model URL, the placeholder key and any timeout settings the gate proves necessary. Test each subclass as `official/tests/test_hermes_local.py` tests Hermes.

**Model connection:** use the same Ollama and `model_relay.py` as every other arm, with the same model and context.
- **Codex** uses the OpenAI Responses API. Point `OPENAI_BASE_URL` at the relay, as Hermes does.
- **Claude Code** uses the Anthropic Messages API: `ANTHROPIC_BASE_URL` (Harbor's `claude_code.py` reads it) and `ANTHROPIC_MODEL`. First check whether your Ollama build serves `/v1/messages` with tool use and streaming. **If it doesn't, stop and tell the user.** A translation proxy would be a new component, so it's a deviation that needs their OK first.

**Keys, the main risk here:**
- Claude Code reads `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN`. The task agent must get only a placeholder value. The real judge key must never reach it, as in every arm.
- The key audit after each set must show 0 real-key lines in the agent containers.
- Before any trial, check that no Claude Code or Codex traffic leaves for a vendor host. All model calls must appear in your relay log, and the egress proxy must allow only the relay host.
- If any call reaches a real API, stop, report it, and don't run more trials. It would cost money and contaminate the arm.

**Effort:** use each harness's highest supported level: Claude Code `--effort max` (Harbor's `reasoning_effort` option) and Codex `reasoning_effort` at its highest value. Record the exact values in the preregistration.

**Gate per harness, before its counted arms:** follow rule 4 of the handoff, with the same parts as the main study's gate 2:
- awilix with no memory, run to its full limit;
- customer delivery with memory;
- one APEX task.

Each harness has its own call timeouts. Hermes needed the D100 settings, and these harnesses may need equivalents. Record any setting you change as a disclosed deviation.

**Analysis (exploratory):**
- Per harness: memory against its own no-memory control (CM vs C0, KM vs K0, HM vs A0), with the same paired sign-flip over tasks.
- Across harnesses: the per-task memory effect compared between harnesses, described, not tested for significance.
- Run `memory_access.py` (shown vs opened) on every trial. Compare the bytes each harness actually shows at the start with the main study's simulated figures (`results/harness-exposure-survey.md`: Codex about 21%, Claude Code about 48%, Hermes 100%).

**Budget:** 4 more sets, about 4 days or more on the A30s. Tell the user your revised timeline when you send the preregistration.

**Effect on your study:** 4 new arms and their gates. The earlier arms don't change.

## U4 (2026-11-04): `check-serving.py` agent-end rule fixed

**Files:** `official/vm/check-serving.py` only.

**Change:** a relay client close is now excused when the call started 1 s after to 10 s before an agent's finish and closed within 60 s after it. The old rule used the close time, from 2 s before to 10 s after the finish. A container teardown once took 18 s, so a harmless background-review close would have failed a set (D104).

**Check:** run it on your gate logs. Harmless closes should start 3–5 s before an agent's end. Closes from a cancel spiral are committed and much older, and must still fail.

**Effect on your study:** this changes only the set check, not how trials run. Pick it up before your next check.
