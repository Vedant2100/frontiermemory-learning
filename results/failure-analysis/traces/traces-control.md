# Trace pass: control arm (fm-tasks-control)

All 45 trial folders are present; the 39 failed trials were opened (trajectory, verifier output, result.json). Control has no memory, so questions 2 to 4 do not apply. Per-trial rows are in `traces-control.jsonl`.

## Counts, old versus new

| Bucket | Old (summary-level) | New (trace-level) | New grade |
|---|---|---|---|
| A1 grader-infeasible | 3 | 3 | O for the failing criterion; the A1 premise comes from the earlier audit |
| A3 task beyond model | 27 | 33 | 30 O, 3 P |
| A7 output missing | 3 | 3 | O |
| D1 undeterminable | 6 | 0 | none left |

No trial has an exception, a timeout or a serving fault. The longest run was 54.7 of 90 minutes, so A4, A5 and A6 stay excluded, now from the trial records.

## D1 resolved (6 trials)

The market-share trials (3) and seat-surplus trials (3) were D1 because the judge rationale and final answer were missing. Both are in the folders. The judge gave specific per-criterion reasons, so a judge that cannot separate right from wrong (A2) is not supported for these trials. Market-share: all three used raw or total ARR where the rubric wants risk-adjusted ARR, a method the prompt does not name. Seat-surplus: two attempts (0.9 and 1.1 minutes) searched only the local disk, found it empty and asked the user for the files. The third attempt reached the data room through the `mcp__world` file tools and got wrong figures. The two short attempts never used those tools, so they are an early stop and not a missing environment. I could not see the tool manifest itself, only that the session text contains no `mcp__world` reference.

## A3 residual: what is behind the 27

None of these is an unexplained capability failure. The trajectories show these mechanisms, which I kept inside A3 because the taxonomy has no finer task-side bucket.

- Hidden preference or convention that the prompt does not state, with functional tests passing (awilix 6, cattrs 2 of 3, customer delivery partly, cookie-store partly). Awilix fails only the version bump to 12.1.0; the explicit variant states "tier 7" with no mapping, the implicit variant says nothing about it. One awilix attempt called the tier "not actionable".
- Choosing between conflicting sources (marketing gap analysis, partnership contract, proposal customization). Passing siblings applied the newer source; failing attempts used the older note or the SOP literally.
- Real functional errors: cookie-store (2 and 12 failing tests), cattrs nested partial structuring, customer delivery re-initialization and cycle handling.
- Reference-defined counting conventions in DAPT (IPv6 inclusion, per-minute binning, flow counting).
- Over-action in the CSM task and a single-target call in all three Teams attempts (grade P, since the check definition is not in the folder).

For these, "needs before blame" says memory could in principle have supplied the preference or convention. The control arm cannot show that; the other arms can.

## Word2Vec A7

All three wrote a component and a model file under other names. The verifier imports `/workspace/solution.py`, which none created, and no test ran. The prompt names no path.

## Eurogrid A1

Five of six criteria pass in all three attempts and the same Avoided Curtailment value (228,025.94 against 243,275.57) fails each time. The reference-fails-too premise is not in the trial folders.

## Still unknown

The meaning of two hidden checks (`strategy_partnership` in proposal customization and the Teams call check) rests on their names and on the task's solution notes, not on a check definition. Whether any related run exists in the corpus for each hidden convention is outside the trial folders.
