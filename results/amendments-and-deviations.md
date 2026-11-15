# Amendments, deviations and incidents

A factual index of every change to the plan, every deviation from the official setup, and every incident that touched counted data. Dates are local (Pacific) and are those written in the plan headings; commit times are in `prereg-timestamps.txt`. "Results seen" says whether any trial result of the affected set or arm was known when the change was made. The full wording of each amendment is in `preregistration-v2.md` (A1 to A7) and `preregistration-arms.md` (B1 to B6); deviations from the official setup are itemised in `protocol-v4-official.md`.

## 1. Plan amendments

| ID | Date | Change | Results seen when made |
|---|---|---|---|
| A1 | Nov 3 | A trial where Hermes gives up on the model server counts as a valid failed attempt, as the official rules count it; each trial records `model_unavailable`, and a sensitivity analysis repeats the main test without those trials. No rerun. | During the first control set; no memory trial |
| A2 | Nov 4 | The first control is discarded and reported as pilot data (3 of 41 trials given up, 420 requests cut by the sandbox proxy); a relay is added in front of the model server; the control is rerun. | Control seen; no memory trial |
| A3 | Nov 4 | Longer watchdog timeouts for model calls (first event 900 s, whole call 1800 s). | Gate trials only; no counted trial |
| A4 | Nov 6 | Run 4 added as the replacement for run 2, whose generation timed out at the 6-hour limit and exported no memory. | Before any run 3 task result |
| A5 | Nov 6 | Exploratory exposure arms reordered; none dropped. | Before any exposure-arm trial |
| A6 | Nov 6 | Placebo and read-first run after run 3 and before run 4. | Before any run 4 or arm trial |
| A7 | Nov 7 | Run 4 runs ahead of read-first (order only) after read-first's uncounted end-to-end check stopped the queue. | Before any run 4 or read-first counted trial |
| B1 | Nov 6 | Codex and Claude Code arms moved to a separate study on a second machine. | Before any arm trial |
| B2 | Nov 6 | Placebo and read-first run first, right after run 3; the recency tests move to the second machine. | Before any arm trial |
| B3 | Nov 6 | Rule for a model-server hang during the placebo set: every trial whose agent ran in the window is set aside and rerun whatever its result; the set's own check stays strict. | During the placebo set, before its result |
| B4 | Nov 8 | Scoped and categorized arms are not run (their inputs are degenerate). | Before any trial of either arm |
| B5 | Nov 9 | The B3 rule applied to the all-shown stalls (10 trials set aside and rerun whatever their result); cue and raw arms not run; the Claude Code and recency tests not run on either machine. | During the none-shown set; the raw all-shown result (5/45) was known and is replaced by the rerun set (7/45); both are reported |
| B6 | Nov 11 | One new exploratory arm, blend, with a written bar fixed in advance. | Before any blend trial |

## 2. Deviations from the official setup

Listed in full, with their reasons, in `protocol-v4-official.md`. In short: the model is local (Qwen3.8-27B, 4-bit, served by Ollama); Docker runs in a virtual machine; the APEX judge is Claude Opus 5.5 instead of the documented GPT-5.6 Sol on three tasks (reference-solution scores reproduced; no agreement test on incorrect outputs); a relay keeps slow model responses alive past the sandbox proxy's 15-second first-byte cut; model-call timeouts are longer; trials run one at a time; one dependency pin is added to the cookie-store verifier's build; builds use one frozen Docker cache and Word2Vec's image is prebuilt. The task time limits are the official ones.

## 3. Incidents that touched counted data

| Date | What happened | What was done | Effect on counted data |
|---|---|---|---|
| Nov 3 to 4 | First control: Hermes gave up on the model server in 3 of 41 trials; the sandbox proxy cut 420 requests. | See A2. | First control not pooled; control rerun in full (45 trials). |
| Nov 4 | First gate failed (Hermes's 300 s cancel spiral on a heavy trial). | See A3; second gate passed before any counted trial. | None. |
| Nov 4 | Serving-check rule for background-review calls cut at container teardown corrected. | Rule changed before the control's check ran; no trial changed. | None. |
| Nov 5 | Run 1's serving check failed on one HTTP 500 caused by the model's malformed tool call (retry answered 200 and the trial finished). | The check's rule narrowed to excuse a parse failure with an identical successful retry; every other 5xx still fails. Made after run 1's results were known; no trial was rerun or excluded. | None. |
| Nov 5 to 6 | Run 2's generation hit the 6-hour limit and exported no memory. | See A4; run 2 has no trials; run 4 replaces it. | 3 memory runs (1, 3, 4) in the main test. |
| Nov 6 | Model-server hang during the placebo set (about 70 minutes). | See B3; one trial set aside and rerun. | Placebo set complete at 45 trials. |
| Nov 7 | Read-first's end-to-end check failed (its sentence was missing from the saved system prompt); a later check confirmed what the model receives. | Held with no counted read-first trial; see A7. | None. |
| Nov 8 | All-shown's first end-to-end check failed on Hermes's short side request, not on the arm. | Check fixed; the trial set aside and rerun. | None. |
| Nov 8 to 9 | Model-server stalls of 15 to 30 minutes during the all-shown set; 10 of 45 trials ended by timeout. | See B5; the 10 trials rerun with no serving fault. | All-shown: 7/45 after the rerun (5/45 before). |
| Nov 9 to 11 | Generator arm: a second generation hit the 6-hour limit and exported no memory. | Reported as not run, as the arms plan says. | None. |
| Nov 11 | Blend arm: one of 15 task rewrites failed the contract check twice. | That task is left out of the blend comparison. | 14 tasks compared. |

## 4. What was not run

Cue, raw corpus, scoped and categorized memory (B4, B5); the Claude Code and recency tests (B5); the generator arm (no memory could be produced). The second machine's Codex pair (6/45 without memory, 7/45 with it) is a separate study and is never compared with these numbers.
