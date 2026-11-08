#!/bin/bash
# A7 (D127): after run 4 (next-study-run4.sh) -- read-first (arms B2) with the D126 checks, then the all-shown exposure
# arm (A5), then the remaining arms through next-study-3.sh. From next-study-2.sh: the same helpers and checks, the
# fast-track block cut to read-first only, run 4's section replaced by a check that run 4 is complete. Run by the hold:
# echo official/vm/next-study-4.sh > official/vm/NEXT. Any failure writes official/vm/STUDY_STOPPED and holds. Always exits 0.
REPO=/home/csgrad/vbork001/frontiermemory-experiment-20261024; cd "$REPO" || exit 0
OLOG=/scratch/$USER/fm-vm/ollama-$SLURM_JOB_ID; LOGF=$REPO/official/logs/study-$SLURM_JOB_ID.log; RES=$REPO/results/official  # same log as the first driver, appended
L0=$(wc -l < "$LOGF" 2>/dev/null || echo 0)  # D129: a check reads only the log lines written since the step it follows began
rm -f official/vm/STUDY_STOPPED
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $*"; }
gpus_free() { for _ in $(seq 1 12); do u=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | sort -n | tail -1); [ "$u" -lt 1000 ] && return 0; pkill -u "$USER" -x ollama; sleep 5; done; return 1; }
stop() { step "STUDY_STOPPED: $*"; echo "$(date) $*" > official/vm/STUDY_STOPPED; exit 0; }
[ -f official/vm/GATE_PASSED ] || stop "gate has not passed"

complete() {  # summary exists with the expected number of finished, valid trials
  python3 - "$RES/summary-$1.jsonl" "$2" <<'PY'
import json, sys
try: rows = [json.loads(l) for l in open(sys.argv[1])]
except FileNotFoundError: sys.exit(1)
sys.exit(0 if len(rows) == int(sys.argv[2]) and all(r.get("finished") and r.get("valid") for r in rows) else 1)
PY
}

trials_ok() {  # $1 summary name, $2 expected trials: all valid, none given up on the model server
  python3 - "$RES/summary-$1.jsonl" "$2" <<'PY'
import collections, json, sys
try: rows = [json.loads(l) for l in open(sys.argv[1])]
except FileNotFoundError: print("TRIALS: FAIL: no summary"); sys.exit(1)
bad = []
if len(rows) != int(sys.argv[2]): bad.append(f"{len(rows)} trials, expected {sys.argv[2]}")
for k, msg in (("valid", "invalid"), ("finished", "unfinished")):
    n = sum(not r.get(k) for r in rows)
    if n: bad.append(f"{n} {msg}")
n = sum(bool(r.get("model_unavailable")) for r in rows)
if n: bad.append(f"{n} model_unavailable")
j = collections.Counter(r.get("judge_status") for r in rows if r.get("judge_status"))
print(f"trials {len(rows)}, passed {sum(bool(r.get('passed')) for r in rows)}, judge {dict(j)}")
print("TRIALS:", "ok" if not bad else "FAIL: " + "; ".join(bad))
sys.exit(1 if bad else 0)
PY
}

run_checked() {  # $1 label, $2 summary name, $3 expected trials, rest: command
  local label=$1 name=$2 n=$3; shift 3
  if complete "$name" "$n"; then step "$label: already complete"; return 0; fi
  gpus_free || stop "$label: GPUs not free"
  local s0 r0; s0=$(wc -l < "$OLOG/server.log" 2>/dev/null || echo 0); r0=$(wc -l < "$OLOG/relay.log" 2>/dev/null || echo 0)
  L0=$(wc -l < "$LOGF" 2>/dev/null || echo 0)  # D129: checks read only what this step wrote
  step "$label: start"
  "$@" 2>&1 | tee -a "$LOGF"
  if tail -n +$((L0+1)) "$LOGF" | grep -q "NO_VALID_MEMORY"; then step "$label: NO_VALID_MEMORY (prereg: reported, trials not run)"; return 1; fi
  python3 official/vm/check-serving.py "$OLOG" "$s0" "$r0" | tee -a "$LOGF"; [ "${PIPESTATUS[0]}" = 0 ] || stop "$label: serving check failed"
  trials_ok "$name" "$n" | tee -a "$LOGF"; [ "${PIPESTATUS[0]}" = 0 ] || stop "$label: trial check failed"
  step "$label: SET_CHECKED"
}

grep -q "run3: SET_CHECKED" "$REPO/official/logs/set-$SLURM_JOB_ID.log" || stop "run 3 has not passed its checks; run 4 waits"
step "study, part 2: full key audits of the finished sets (every line must read real_key_lines=0)"
( source official/vm/lib.sh; vm_boot 4 8G || exit 1
  G 'cd ~ && for f in key-audit-control.log key-audit-run1.log key-audit-run2.log key-audit-run3.log key-audit-run4.log; do [ -e $f ] || continue; n=$(grep -c . $f); z=$(grep -c "real_key_lines=0$" $f); echo "$f lines=$n zero=$z"; [ "$n" = "$z" ] || exit 1; done'
  rc=$?; vm_stop; exit $rc ) || stop "key audit of a finished set is not all zero, or could not be read"

for s in control run1 run3; do complete "fm-tasks-$s" 45 || stop "$s is not complete"; done
for s in run4; do complete "fm-tasks-$s" 45 || stop "$s is not complete; this driver runs after run 4"; done
[ -f official/vm/RUN4_PENDING ] && stop "RUN4_PENDING still set"
grep -q "run 4 done and checked (A7)" "$REPO/official/logs/set-$SLURM_JOB_ID.log" || stop "run 4's driver has not finished its checks"
# A7, D126: read-first with the checks that read the API-time prompt. Its Nov 7 e2e trial (failed by the old check) is set
# aside, kept, so the e2e step runs a fresh trial: resuming the finished one would send no traffic and fail the serving check.
if ! complete fm-tasks-arm-readfirst 45; then
  if ! complete fm-smoke-arm-readfirst 1; then
    ( source official/vm/lib.sh; vm_boot 4 8G || exit 1
      G 'cd ~/official/frontiermemory/jobs && if [ -d fm-smoke-arm-readfirst ]; then [ ! -e fm-smoke-arm-readfirst.d125 ] && sudo mv fm-smoke-arm-readfirst fm-smoke-arm-readfirst.d125; fi; [ ! -e fm-smoke-arm-readfirst ]'
      rc=$?; vm_stop; exit $rc ) || stop "could not set aside the Nov 7 read-first e2e (D126)"
    step "read-first: Nov 7 e2e set aside as fm-smoke-arm-readfirst.d125"
  fi
  step "read-first (arms B2, after run 4 per A7)"
  ARMS="readfirst" ARMS_PRE="control run1 run3 run4" bash official/vm/next-study-3.sh
  [ -f official/vm/STUDY_STOPPED ] && stop "read-first stopped: $(cat official/vm/STUDY_STOPPED)"
fi

for arm in all; do  # A5: none-shown runs later, inside the arms order (next-study-3.sh), as cue's control
  run_checked "exposure-$arm e2e" "fm-smoke-exposure-$arm" 1 env E2E=1 bash official/vm/run-exposure.sh "$arm"
  tail -n +$((L0+1)) "$LOGF" | grep -q "EXPOSURE_CHECK_FAILED\|NO_RUN1_MEMORY_FAILED\|run-set-v1.sbatch changed" && stop "exposure-$arm: end-to-end check failed"
  run_checked "exposure-$arm" "fm-tasks-exposure-$arm" 45 bash official/vm/run-exposure.sh "$arm"
done

step "PREREGISTERED_SETS_DONE: control, run 1, run 3, run 4, exposure-all (A5)"
if git -C "$REPO" rev-parse -q --verify refs/tags/prereg-arms >/dev/null && [ -f "$REPO/official/vm/next-study-3.sh" ]; then
  echo official/vm/next-study-3.sh > official/vm/NEXT; step "next: the exploratory arms (next-study-3.sh), in this allocation"
else
  step "HOLD: arms not approved or not merged; the job keeps the GPUs until NEXT or DRIVER_DONE"
fi
exit 0
