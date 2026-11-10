#!/bin/bash
# Arms amendment B5 (2026-11-09). Queued in official/vm/NEXT; the hold runs it after next-study-3.sh hands over once the
# none-shown set is checked. Holds (does nothing) unless none-shown is complete and nothing stopped the study.
# 1. all-shown (D136): re-check its serving with only the nine stall windows left out; set aside the 10 trials whose agent
#    ran in a window (kept in fm-tasks-exposure-all.incident-d136/), whatever their result; rerun them by resuming the set;
#    the rerun's own serving and trial checks, nothing excused.
# 2. then evidence and generator through next-study-3.sh (ARMS subset: same checks as every arm);
# 3. then DRIVER_DONE, which releases the job. Always exits 0.
REPO=/home/csgrad/vbork001/frontiermemory-experiment-20261024; cd "$REPO" || exit 0
OLOG=/scratch/$USER/fm-vm/ollama-$SLURM_JOB_ID; LOGF=$REPO/official/logs/study-arms-$SLURM_JOB_ID.log; RES=$REPO/results/official
INC=$REPO/official/vm/serving-incidents-d136.json; JOB=fm-tasks-exposure-all
S0=8802878; R0=14536; SE=9709860; RE=16259  # the all-shown set's Ollama and relay lines (Nov 8 12:33 to Nov 9 10:54), measured Nov 9
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $*"; }
gpus_free() { for _ in $(seq 1 12); do u=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | sort -n | tail -1); [ "$u" -lt 1000 ] && return 0; pkill -u "$USER" -x ollama; sleep 5; done; return 1; }
hold() { step "B5: HOLD: $*"; echo "$(date) B5: $*" > official/vm/STUDY_STOPPED; exit 0; }
complete() { python3 - "$RES/summary-$1.jsonl" "$2" <<'PY'
import json, sys
try: rows = [json.loads(l) for l in open(sys.argv[1])]
except FileNotFoundError: sys.exit(1)
sys.exit(0 if len(rows) == int(sys.argv[2]) and all(r.get("finished") and r.get("valid") for r in rows) else 1)
PY
}

[ -f official/vm/STUDY_STOPPED ] && { step "B5: the study is stopped ($(cat official/vm/STUDY_STOPPED)); nothing done, holding"; exit 0; }
complete fm-tasks-exposure-none 45 || { step "B5: none-shown is not complete; nothing done, holding"; exit 0; }
# The hand-over stops next-study-3.sh between sets; make sure no VM from it is left running.
pkill -u "$USER" -f qemu-kvm 2>/dev/null && sleep 20

if ! grep -qs "B5: all-shown rerun checked" "$LOGF"; then
  step "B5 (D136): all-shown serving re-check with only the nine stall windows left out"
  CHK="$OLOG/d136chk"; mkdir -p "$CHK" || hold "could not make $CHK"
  head -n $((SE-1)) "$OLOG/server.log" > "$CHK/server.log"; head -n $((RE-1)) "$OLOG/relay.log" > "$CHK/relay.log"
  python3 official/vm/check-serving.py "$CHK" "$S0" "$R0" --incidents "$INC" | tee -a "$LOGF"
  [ "${PIPESTATUS[0]}" = 0 ] || hold "all-shown serving faults outside the D136 windows"
  TR=$(python3 - "$RES/summary-$JOB.jsonl" "$INC" <<'PY'
import datetime as dt, json, sys
w = [(dt.datetime.fromisoformat(x["start"]).timestamp(), dt.datetime.fromisoformat(x["end"]).timestamp()) for x in json.load(open(sys.argv[2]))]
ts = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() if s else None
for r in map(json.loads, open(sys.argv[1])):
    a, b = ts(r.get("agent_started")), ts(r.get("agent_finished"))
    if a is not None and any(a <= hi and (b is None or b >= lo) for lo, hi in w): print(r["trial"])
PY
) || hold "could not read the all-shown summary"
  [ "$(echo $TR | wc -w)" = 10 ] || hold "expected the 10 trials fixed in B5, found $(echo $TR | wc -w): $TR"
  step "B5: setting aside the 10 trials: $TR"
  ( source official/vm/lib.sh; vm_boot 4 8G || exit 1
    n=$(G "cd ~/official/frontiermemory/jobs && sudo mkdir -p $JOB.incident-d136 && for t in $TR; do sudo mv $JOB/\$t $JOB.incident-d136/ || exit 1; done; ls $JOB.incident-d136 | wc -l"); rc=$?
    echo "set aside: $n"; vm_stop; [ "$rc" = 0 ] && [ "$n" = 10 ] ) || hold "could not set the incident trials aside"
  gpus_free || hold "GPUs not free for the rerun"
  s0=$(wc -l < "$OLOG/server.log"); r0=$(wc -l < "$OLOG/relay.log"); L0=$(wc -l < "$LOGF")
  step "B5: rerunning the 10 trials by resuming the all-shown set"
  bash official/vm/run-exposure.sh all 2>&1 | tee -a "$LOGF"
  tail -n +$((L0+1)) "$LOGF" | grep -q "EXPOSURE_CHECK_FAILED\|NO_RUN1_MEMORY_FAILED\|run-set-v1.sbatch changed" && hold "all-shown arm check failed on the rerun"
  python3 official/vm/check-serving.py "$OLOG" "$s0" "$r0" | tee -a "$LOGF"; [ "${PIPESTATUS[0]}" = 0 ] || hold "all-shown rerun serving check failed"
  python3 - "$RES/summary-$JOB.jsonl" <<'PY' | tee -a "$LOGF"; [ "${PIPESTATUS[0]}" = 0 ] || hold "all-shown trial check failed after the rerun"
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
bad = [f"{len(rows)} trials"] * (len(rows) != 45) + [f"{sum(not r.get(k) for r in rows)} not {k}" for k in ("valid", "finished") if any(not r.get(k) for r in rows)]
bad += [f"{sum(bool(r.get('model_unavailable')) for r in rows)} model_unavailable"] * any(r.get("model_unavailable") for r in rows)
print(f"trials {len(rows)}, passed {sum(bool(r.get('passed')) for r in rows)}"); print("TRIALS:", "ok" if not bad else "FAIL: " + "; ".join(bad))
sys.exit(1 if bad else 0)
PY
  step "B5: all-shown rerun checked"
fi

step "B5: evidence and generator (next-study-3.sh, ARMS subset)"
ARMS="evidence generator" bash official/vm/next-study-3.sh
[ -f official/vm/STUDY_STOPPED ] && { step "B5: an arm stopped the study; holding"; exit 0; }
step "B5: ARMS_DONE (none-shown, all-shown rerun, evidence, generator); releasing the job"; date > official/vm/DRIVER_DONE
exit 0
