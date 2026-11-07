#!/bin/bash
# D123, arms amendment B3: recover the placebo arm from the documented D122 Ollama hang, then continue the study.
# Queued in official/vm/NEXT before the placebo set ends; the hold runs it when the placebo set stops on its serving check,
# as it must (its check doesn't know the incident). Any other stop: it does nothing and the job holds, as before.
# 1. the placebo set's serving check again, with only the D122 window left out (official/vm/serving-incidents.json);
# 2. every placebo trial whose agent ran during the window is set aside (kept in fm-tasks-arm-placebo.incident-d122/),
#    whatever its result, and rerun by resuming the set (the same path as the official no-reward rerun);
# 3. the rerun's own serving, arm and trial checks, with no incident excused;
# 4. then the study continues: next-study-2.sh (read-first, run 4, all-shown, then the arms). Always exits 0.
REPO=/home/csgrad/vbork001/frontiermemory-experiment-20261024; cd "$REPO" || exit 0
OLOG=/scratch/$USER/fm-vm/ollama-$SLURM_JOB_ID; LOGF=$REPO/official/logs/study-arms-$SLURM_JOB_ID.log; RES=$REPO/results/official
INC=$REPO/official/vm/serving-incidents.json; JOB=fm-tasks-arm-placebo
S0=5492267; R0=7753  # first Ollama and relay lines of the placebo set (14:38:35, 14:38:37), measured on Nov 6 (D123)
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $*"; }
gpus_free() { for _ in $(seq 1 12); do u=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | sort -n | tail -1); [ "$u" -lt 1000 ] && return 0; pkill -u "$USER" -x ollama; sleep 5; done; return 1; }
hold() { step "D122 recovery: HOLD: $*"; echo "$(date) D122 recovery: $*" > official/vm/STUDY_STOPPED; exit 0; }

grep -qs "arm-placebo: serving check failed\|arm-placebo: trial check failed" official/vm/STUDY_STOPPED || {
  step "D122 recovery: not the expected stop ($(cat official/vm/STUDY_STOPPED 2>/dev/null)); nothing done, holding"; exit 0; }
step "D122 recovery (B3): the placebo set stopped as expected; re-checking it with only the D122 window left out"
python3 official/vm/check-serving.py "$OLOG" "$S0" "$R0" --incidents "$INC" | tee -a "$LOGF"
[ "${PIPESTATUS[0]}" = 0 ] || hold "placebo serving faults outside the D122 window"

T=$(python3 - "$RES/summary-$JOB.jsonl" "$INC" <<'PY'
import datetime as dt, json, sys
w = [(dt.datetime.fromisoformat(x["start"]).timestamp(), dt.datetime.fromisoformat(x["end"]).timestamp()) for x in json.load(open(sys.argv[2]))]
ts = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() if s else None
for r in map(json.loads, open(sys.argv[1])):
    a, b = ts(r.get("agent_started")), ts(r.get("agent_finished"))
    if a is not None and any(a <= hi and (b is None or b >= lo) for lo, hi in w): print(r["trial"])
PY
) || hold "could not read the placebo summary"
step "D122 recovery: trials whose agent ran during the window: $(echo $T | wc -w) ($T)"
if [ -n "$T" ]; then
  ( source official/vm/lib.sh; vm_boot 4 8G || exit 1
    G "cd ~/official/frontiermemory/jobs && sudo mkdir -p $JOB.incident-d122 && for t in $T; do sudo mv $JOB/\$t $JOB.incident-d122/; done; ls $JOB.incident-d122 | wc -l"
    rc=$?; vm_stop; exit $rc ) || hold "could not set the incident trials aside"
  gpus_free || hold "GPUs not free for the rerun"
  s0=$(wc -l < "$OLOG/server.log"); r0=$(wc -l < "$OLOG/relay.log")
  step "D122 recovery: rerunning the set-aside trial(s) by resuming the placebo set"
  bash official/vm/run-arm.sh placebo 2>&1 | tee -a "$LOGF"
  tail -80 "$LOGF" | grep -q "ARM_CHECK_FAILED\|PLACEBO_BUILD_FAILED\|run-set-v1.sbatch changed" && hold "placebo arm check failed on the rerun"
  python3 official/vm/check-serving.py "$OLOG" "$s0" "$r0" | tee -a "$LOGF"; [ "${PIPESTATUS[0]}" = 0 ] || hold "rerun serving check failed"
fi
python3 - "$RES/summary-$JOB.jsonl" <<'PY' | tee -a "$LOGF"; [ "${PIPESTATUS[0]}" = 0 ] || hold "placebo trial check failed after the rerun"
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
bad = [f"{len(rows)} trials"] * (len(rows) != 45) + [f"{sum(not r.get(k) for r in rows)} not {k}" for k in ("valid", "finished") if any(not r.get(k) for r in rows)]
bad += [f"{sum(bool(r.get('model_unavailable')) for r in rows)} model_unavailable"] * any(r.get("model_unavailable") for r in rows)
print(f"trials {len(rows)}, passed {sum(bool(r.get('passed')) for r in rows)}"); print("TRIALS:", "ok" if not bad else "FAIL: " + "; ".join(bad))
sys.exit(1 if bad else 0)
PY
rm -f official/vm/STUDY_STOPPED
step "D122 recovery: placebo complete and checked; continuing with next-study-2.sh"
exec bash official/vm/next-study-2.sh
