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
