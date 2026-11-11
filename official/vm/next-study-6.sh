#!/bin/bash
# B6 driver (results/preregistration-arms.md): a copy of next-study-3.sh whose only arm is blend, run through run-blend.sh.
# Holds unless the generator arm is finished; refuses to start after Nov 16 06:00 (the arm needs about 18 h before the job ends).
# Original header follows.
# The exploratory arms of results/preregistration-arms.md, in its order, after the preregistered study (runs 1-4 and the two
# exposure arms) has finished. Run by run-arms.sbatch, a new held job: nothing here touches the running study's job.
# Refuses to start unless the arms preregistration is tagged prereg-arms (user approval) and the exposure arms are complete.
# Each arm: a one-trial uncounted end-to-end check (E2E=1), then 45 counted trials; the Codex and Claude Code arms first need
# their own full gate (next-gate-harness.sh); the recency arms are generation plus a probe, no task trials. After each set:
# serving check and trial check, as next-study-2.sh. Any failure writes official/vm/STUDY_STOPPED and exits; rerunning skips
# finished sets. ARMS="a b" limits the run to those arms, in the preregistered order. STAGE=checks runs only the effort
# probe (effort-check.sh), the harness gates and each arm's end-to-end check (recency arms skipped: generation is the arm),
# so every arm is exercised for real before ~8 days of counted sets. Always exits 0.
REPO=$HOME/frontiermemory-experiment-20261024; cd "$REPO" || exit 0
OLOG=/scratch/$USER/fm-vm/ollama-$SLURM_JOB_ID; LOGF=$REPO/official/logs/study-arms-$SLURM_JOB_ID.log; RES=$REPO/results/official
L0=$(wc -l < "$LOGF" 2>/dev/null || echo 0)  # D129: a check reads only the log lines written since the step it follows began
ORDER="blend"  # B6 (2026-11-11): the blend arm, after the generator arm; the old order was  # prereg order, A5; c0 cm k0 km (B1) and recency (B2) on the second machine; scoped and categorized dropped (B4, D135: one skill per memory)
rm -f official/vm/STUDY_STOPPED
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $*"; }
gpus_free() { for _ in $(seq 1 12); do u=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | sort -n | tail -1); [ "$u" -lt 1000 ] && return 0; pkill -u "$USER" -x ollama; sleep 5; done; return 1; }
stop() { step "STUDY_STOPPED: $*"; echo "$(date) $*" > official/vm/STUDY_STOPPED; exit 0; }

[ "$(date +%s)" -le "$(date -d '2026-11-16 06:00' +%s)" ] || { step "blend: past the B6 cutoff (Nov 16 06:00); not run (time)"; date > official/vm/DRIVER_DONE; exit 0; }
git rev-parse -q --verify refs/tags/prereg-arms >/dev/null || stop "results/preregistration-arms.md is not tagged prereg-arms (not approved)"
complete() {  # summary exists with the expected number of finished, valid trials
  python3 - "$RES/summary-$1.jsonl" "$2" <<'PY'
import json, sys
try: rows = [json.loads(l) for l in open(sys.argv[1])]
except FileNotFoundError: sys.exit(1)
sys.exit(0 if len(rows) == int(sys.argv[2]) and all(r.get("finished") and r.get("valid") for r in rows) else 1)
PY
}
for s in ${ARMS_PRE:-control run1 run3 run4 exposure-all}; do complete "fm-tasks-$s" 45 || stop "$s is not complete; the arms run after the preregistered sets"; done  # A5: exposure-none runs in ORDER; B2: the fast-track call sets ARMS_PRE

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
  case "$name" in fm-smoke-*)  # D134: an uncounted test run whose job exists but never reached a summary failed earlier. Resuming a
    # finished trial sends no traffic and fails the serving check (D124, D129, D133), so set it aside, kept, and run a fresh one.
    if [ ! -f "$RES/summary-$name.jsonl" ]; then
      ( source official/vm/lib.sh; vm_boot 4 8G || exit 1
        G "cd ~/official/frontiermemory/jobs && if [ -d $name ]; then sudo mv $name $name.aside-\$(date +%s); fi; [ ! -e $name ]"
        rc=$?; vm_stop; exit $rc ) || stop "$label: could not set aside the earlier test run (D134)"
    fi ;;
  esac
  local s0 r0; s0=$(wc -l < "$OLOG/server.log" 2>/dev/null || echo 0); r0=$(wc -l < "$OLOG/relay.log" 2>/dev/null || echo 0)
  L0=$(wc -l < "$LOGF" 2>/dev/null || echo 0)  # D129: checks read only what this step wrote
  step "$label: start"
  "$@" 2>&1 | tee -a "$LOGF"
  if tail -n +$((L0+1)) "$LOGF" | grep -q "NO_VALID_MEMORY"; then step "$label: NO_VALID_MEMORY (prereg: reported, trials not run)"; return 1; fi
  tail -n +$((L0+1)) "$LOGF" | grep -q "ARM_CHECK_FAILED\|NO_RUN1_MEMORY_FAILED\|BLEND_REWRITE_FAILED\|BLEND_CHECK: FAIL\|run-set-v1.sbatch changed" && stop "$label: arm check failed"
  python3 official/vm/check-serving.py "$OLOG" "$s0" "$r0" | tee -a "$LOGF"; [ "${PIPESTATUS[0]}" = 0 ] || stop "$label: serving check failed"
  trials_ok "$name" "$n" | tee -a "$LOGF"; [ "${PIPESTATUS[0]}" = 0 ] || stop "$label: trial check failed"
  step "$label: SET_CHECKED"
}

recency_checked() {  # generation and probe only
  local arm=$1
  if [ -f "$RES/recency-probe-arm-$arm.txt" ] && grep -q RECENCY_PROBE "$RES/recency-probe-arm-$arm.txt"; then step "$arm: already complete"; return 0; fi
  gpus_free || stop "$arm: GPUs not free"
  local s0 r0; s0=$(wc -l < "$OLOG/server.log" 2>/dev/null || echo 0); r0=$(wc -l < "$OLOG/relay.log" 2>/dev/null || echo 0)
  L0=$(wc -l < "$LOGF" 2>/dev/null || echo 0)  # D129
  step "$arm: start"
  bash official/vm/run-blend.sh "$arm" 2>&1 | tee -a "$LOGF"
  tail -n +$((L0+1)) "$LOGF" | grep -q "RECENCY_CORPUS_FAILED\|run-set-v1.sbatch changed" && stop "$arm: corpus build failed"
  if tail -n +$((L0+1)) "$LOGF" | grep -q "NO_VALID_MEMORY"; then step "$arm: NO_VALID_MEMORY (prereg: reported, no probe)"; return 0; fi
  python3 official/vm/check-serving.py "$OLOG" "$s0" "$r0" | tee -a "$LOGF"; [ "${PIPESTATUS[0]}" = 0 ] || stop "$arm: serving check failed"
  grep -q RECENCY_PROBE "$RES/recency-probe-arm-$arm.txt" 2>/dev/null || stop "$arm: no probe result"
  step "$arm: SET_CHECKED"
}

if ! grep -qs "EFFORT_PROBE_DONE\|EFFORT_PROBE_REJECTED" "$RES"/effort-probe-*.txt; then  # once, before any arm
  gpus_free || stop "effort probe: GPUs not free"
  step "effort probe (effort-check.sh): does the server act on each harness's effort setting?"
  bash official/vm/effort-check.sh 2>&1 | tee -a "$LOGF"  # reported either way; a refused setting also shows in the gates
fi

for arm in $ORDER; do
  case " ${ARMS:-$ORDER} " in *" $arm "*) ;; *) continue ;; esac
  if [ "$arm" = exposure-none ]; then  # A5: the preregistered none-shown arm (A2), here as cue's control
    run_checked "exposure-none e2e" fm-smoke-exposure-none 1 env E2E=1 bash official/vm/run-exposure.sh none || continue
    tail -n +$((L0+1)) "$LOGF" | grep -q "EXPOSURE_CHECK_FAILED\|NO_RUN1_MEMORY_FAILED\|run-set-v1.sbatch changed\|RUN4_PENDING" && stop "exposure-none: end-to-end check failed"
    [ "${STAGE:-all}" = checks ] && continue
    run_checked exposure-none fm-tasks-exposure-none 45 bash official/vm/run-exposure.sh none
    continue
  fi
  case "$arm" in
    recency-*) [ "${STAGE:-all}" = checks ] && continue; recency_checked "$arm"; continue ;;
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
  run_checked "arm-$arm e2e" "fm-smoke-arm-$arm" 1 env E2E=1 bash official/vm/run-blend.sh "$arm" || continue
  [ "${STAGE:-all}" = checks ] && continue  # checks only: no counted set
  run_checked "arm-$arm" "fm-tasks-arm-$arm" 45 bash official/vm/run-blend.sh "$arm" || continue
  ( python3 -I scripts/analyze_arms.py --dir results/official 2>&1 | tail -5 | cut -c1-170 ) | tee -a "$LOGF"
done

[ "${STAGE:-all}" = checks ] && { step "ARM_CHECKS_DONE: effort probe, harness gates and every arm's end-to-end check; no counted set run"; exit 0; }
if [ -n "${ARMS:-}" ]; then step "ARMS_DONE for: $ARMS (a subset; the job is not released)"; exit 0; fi
step "ARMS_DONE"; date > official/vm/DRIVER_DONE  # releases the held allocation
exit 0
