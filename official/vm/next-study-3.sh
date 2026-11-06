#!/bin/bash
# The exploratory arms of results/preregistration-arms.md, in its order, after the preregistered study (runs 1-4 and the two
# exposure arms) has finished. Run by run-arms.sbatch, a new held job: nothing here touches the running study's job.
# Refuses to start unless the arms preregistration is tagged prereg-arms (user approval) and the exposure arms are complete.
# Each arm: a one-trial uncounted end-to-end check (E2E=1), then 45 counted trials; the Codex and Claude Code arms first need
# their own full gate (next-gate-harness.sh); the recency arms are generation plus a probe, no task trials. After each set:
# serving check and trial check, as next-study-2.sh. Any failure writes official/vm/STUDY_STOPPED and exits; rerunning skips
# finished sets. ARMS="a b" limits the run to those arms, in the preregistered order. Always exits 0.
REPO=$HOME/frontiermemory-experiment-20261024; cd "$REPO" || exit 0
OLOG=/scratch/$USER/fm-vm/ollama-$SLURM_JOB_ID; LOGF=$REPO/official/logs/study-arms-$SLURM_JOB_ID.log; RES=$REPO/results/official
ORDER="placebo readfirst cue scoped evidence raw generator c0 cm k0 km recency-a recency-b categorized"  # prereg order
rm -f official/vm/STUDY_STOPPED
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $*"; }
gpus_free() { for _ in $(seq 1 12); do u=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | sort -n | tail -1); [ "$u" -lt 1000 ] && return 0; pkill -u "$USER" -x ollama; sleep 5; done; return 1; }
stop() { step "STUDY_STOPPED: $*"; echo "$(date) $*" > official/vm/STUDY_STOPPED; exit 0; }

git rev-parse -q --verify refs/tags/prereg-arms >/dev/null || stop "results/preregistration-arms.md is not tagged prereg-arms (not approved)"
complete() {  # summary exists with the expected number of finished, valid trials
  python3 - "$RES/summary-$1.jsonl" "$2" <<'PY'
import json, sys
try: rows = [json.loads(l) for l in open(sys.argv[1])]
except FileNotFoundError: sys.exit(1)
sys.exit(0 if len(rows) == int(sys.argv[2]) and all(r.get("finished") and r.get("valid") for r in rows) else 1)
PY
}
for s in control run1 run3 run4 exposure-none exposure-all; do complete "fm-tasks-$s" 45 || stop "$s is not complete; the arms run after the preregistered sets"; done

trials_ok() {  # $1 summary name, $2 expected trials: all valid and finished, none given up on the model server
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
  if tail -60 "$LOGF" | grep -q "NO_VALID_MEMORY"; then step "$label: NO_VALID_MEMORY (prereg: reported, trials not run)"; return 1; fi
  tail -80 "$LOGF" | grep -q "ARM_CHECK_FAILED\|NO_RUN1_MEMORY_FAILED\|PLACEBO_BUILD_FAILED\|run-set-v1.sbatch changed" && stop "$label: arm check failed"
  python3 official/vm/check-serving.py "$OLOG" "$s0" "$r0" | tee -a "$LOGF"; [ "${PIPESTATUS[0]}" = 0 ] || stop "$label: serving check failed"
  trials_ok "$name" "$n" | tee -a "$LOGF"; [ "${PIPESTATUS[0]}" = 0 ] || stop "$label: trial check failed"
  step "$label: SET_CHECKED"
}

recency_checked() {  # generation and probe only
  local arm=$1
  if [ -f "$RES/recency-probe-arm-$arm.txt" ] && grep -q RECENCY_PROBE "$RES/recency-probe-arm-$arm.txt"; then step "$arm: already complete"; return 0; fi
  gpus_free || stop "$arm: GPUs not free"
  local s0 r0; s0=$(wc -l < "$OLOG/server.log" 2>/dev/null || echo 0); r0=$(wc -l < "$OLOG/relay.log" 2>/dev/null || echo 0)
  step "$arm: start"
  bash official/vm/run-arm.sh "$arm" 2>&1 | tee -a "$LOGF"
  tail -60 "$LOGF" | grep -q "RECENCY_CORPUS_FAILED\|run-set-v1.sbatch changed" && stop "$arm: corpus build failed"
  if tail -60 "$LOGF" | grep -q "NO_VALID_MEMORY"; then step "$arm: NO_VALID_MEMORY (prereg: reported, no probe)"; return 0; fi
  python3 official/vm/check-serving.py "$OLOG" "$s0" "$r0" | tee -a "$LOGF"; [ "${PIPESTATUS[0]}" = 0 ] || stop "$arm: serving check failed"
  grep -q RECENCY_PROBE "$RES/recency-probe-arm-$arm.txt" 2>/dev/null || stop "$arm: no probe result"
  step "$arm: SET_CHECKED"
}

for arm in $ORDER; do
  case " ${ARMS:-$ORDER} " in *" $arm "*) ;; *) continue ;; esac
  case "$arm" in
    recency-*) recency_checked "$arm"; continue ;;
    c0|cm) g=CODEX; h=codex ;;
    k0|km) g=CLAUDE; h=claude ;;
    *) g="" ;;
  esac
  if [ -n "$g" ] && [ ! -f "official/vm/GATE_PASSED_$g" ]; then
    gpus_free || stop "$h gate: GPUs not free"
    bash official/vm/next-gate-harness.sh "$h" 2>&1 | tee -a "$LOGF"
    [ -f "official/vm/GATE_PASSED_$g" ] || stop "$h gate failed"
  fi
  # run_checked returns 1 only for NO_VALID_MEMORY: reported, and that arm's trials are not run (prereg)
  run_checked "arm-$arm e2e" "fm-smoke-arm-$arm" 1 env E2E=1 bash official/vm/run-arm.sh "$arm" || continue
  run_checked "arm-$arm" "fm-tasks-arm-$arm" 45 bash official/vm/run-arm.sh "$arm" || continue
  ( python3 -I scripts/analyze_arms.py --dir results/official 2>&1 | tail -5 | cut -c1-170 ) | tee -a "$LOGF"
done

step "ARMS_DONE"
exit 0
