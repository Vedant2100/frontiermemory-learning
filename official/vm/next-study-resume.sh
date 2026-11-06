#!/bin/bash
# Resume of next-study.sh after a STUDY_STOPPED (D107). Same sets, checks and order; the gate's key-audit renaming is replaced by a
# full check of the finished sets' key audits. Run by the hold: echo official/vm/next-study-resume.sh > official/vm/NEXT
# control -> run1 -> run2 -> run3 through run-set-v1.sbatch, then the exploratory exposure arms (none, then all), each after a
# one-trial uncounted end-to-end check. After each set: serving checks (check-serving.py) and trial checks. Any failure writes
# official/vm/STUDY_STOPPED and returns to the hold; rerunning this driver skips finished sets and resumes the rest.
# At the end it writes official/vm/DRIVER_DONE, so the job releases the GPUs. Always exits 0.
REPO=/home/csgrad/vbork001/frontiermemory-experiment-20261024; cd "$REPO" || exit 0
OLOG=/scratch/$USER/fm-vm/ollama-$SLURM_JOB_ID; LOGF=$REPO/official/logs/study-$SLURM_JOB_ID.log; RES=$REPO/results/official  # same log as the first driver, appended
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
  step "$label: start"
  "$@" 2>&1 | tee -a "$LOGF"
  if tail -40 "$LOGF" | grep -q "NO_VALID_MEMORY"; then step "$label: NO_VALID_MEMORY (prereg: reported, trials not run)"; return 1; fi
  python3 official/vm/check-serving.py "$OLOG" "$s0" "$r0" | tee -a "$LOGF"; [ "${PIPESTATUS[0]}" = 0 ] || stop "$label: serving check failed"
  trials_ok "$name" "$n" | tee -a "$LOGF"; [ "${PIPESTATUS[0]}" = 0 ] || stop "$label: trial check failed"
  step "$label: SET_CHECKED"
}

step "study resume: full key audits of the finished sets (every line must read real_key_lines=0)"
( source official/vm/lib.sh; vm_boot 4 8G || exit 1
  G 'cd ~ && for f in key-audit-control.log key-audit-run1.log key-audit-run2.log key-audit-run3.log; do [ -e $f ] || continue; n=$(grep -c . $f); z=$(grep -c "real_key_lines=0$" $f); echo "$f lines=$n zero=$z"; [ "$n" = "$z" ] || exit 1; done'
  rc=$?; vm_stop; exit $rc ) || stop "key audit of a finished set is not all zero, or could not be read"

for s in control run1 run2 run3; do
  run_checked "$s" "fm-tasks-$s" 45 env SET=$s SMOKE=0 bash official/vm/run-set-v1.sbatch
  ( python3 -I scripts/analyze_official.py --dir results/official 2>&1 | grep -E '"flags"|no reward|judge failed|expected|attempts differ' | cut -c1-170 ) | tee -a "$LOGF"
done

for arm in none all; do
  run_checked "exposure-$arm e2e" "fm-smoke-exposure-$arm" 1 env E2E=1 bash official/vm/run-exposure.sh "$arm"
  tail -60 "$LOGF" | grep -q "EXPOSURE_CHECK_FAILED\|NO_RUN1_MEMORY_FAILED\|run-set-v1.sbatch changed" && stop "exposure-$arm: end-to-end check failed"
  run_checked "exposure-$arm" "fm-tasks-exposure-$arm" 45 bash official/vm/run-exposure.sh "$arm"
done

step "STUDY_DONE"; date > official/vm/DRIVER_DONE
exit 0
