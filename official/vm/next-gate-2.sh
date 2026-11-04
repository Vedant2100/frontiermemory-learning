#!/bin/bash
# Second restart gate (D100), never counted: the first gate (next-gate.sh, job 305865) failed when Hermes gave up on
# customer delivery. Same parts and checks, with Hermes's watchdog settings (hermes_local.py) and the relay's retry
# supersede (model_relay.py). New job names, so nothing of the first gate is resumed or overwritten.
# Run by the hold: echo official/vm/next-gate-2.sh > official/vm/NEXT
# Full settings, relay on, through run-set-v1.sbatch's own code (SMOKE=gate):
#   1. one fresh generation on corpus v1.1 (fm-gen-gate), then customer delivery and one APEX task with that memory (fm-gate-mem)
#   2. awilix-release-tier-implicit, no memory, to its own limit (fm-gate-control): the longest task (D93 rule)
# PASS needs all of: no "client closing the connection" and no HTTP 500 in the Ollama log; in the relay log, keepalives used and no
# upstream error, max-wait drop or client close; every trial valid with a reward on its first round; no model_unavailable;
# APEX judge completed; a valid generation. Writes official/vm/GATE_PASSED or GATE_FAILED and returns to the hold. Always exits 0.
REPO=/home/csgrad/vbork001/frontiermemory-experiment-20261024; cd "$REPO" || exit 0
OLOG=/scratch/$USER/fm-vm/ollama-$SLURM_JOB_ID; G_OUT=$REPO/official/logs/gate-2-$SLURM_JOB_ID.log
rm -f official/vm/GATE_PASSED official/vm/GATE_FAILED
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $*"; }
gpus_free() { for _ in $(seq 1 12); do u=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | sort -n | tail -1); [ "$u" -lt 1000 ] && return 0; pkill -u "$USER" -x ollama; sleep 5; done; return 1; }
fail() { step "GATE_FAILED: $*"; echo "$*" > official/vm/GATE_FAILED; exit 0; }

step "gate 2: keeping the first gate's key-audit logs apart"
( source official/vm/lib.sh; vm_boot 4 8G || exit 1
  G 'cd ~ && for f in key-audit-control.log key-audit-run1.log; do [ -e $f ] && mv $f ${f%.log}.gate1.log; done; ls key-audit* 2>/dev/null'
  vm_stop ) || fail "could not set the first gate's key-audit logs aside"

S0=$(wc -l < "$OLOG/server.log" 2>/dev/null || echo 0); R0=$(wc -l < "$OLOG/relay.log" 2>/dev/null || echo 0)
gpus_free || fail "GPUs not free"
step "gate 1/2: generation, then customer delivery and APEX with that memory"
SET=run1 SMOKE=gate GATE_GENJOB=fm-gen-gate2 GATE_TASKJOB=fm-gate-2-mem GATE_FILTER="-i 'customer-delivery-contextual-preferences' -i 'apex-eurogrid-curtailment'" \
  bash official/vm/run-set-v1.sbatch 2>&1 | tee -a "$G_OUT"
gpus_free || fail "GPUs not free after part 1"
step "gate 2/2: awilix-release-tier-implicit, no memory"
SET=control SMOKE=gate GATE_GENJOB=none GATE_TASKJOB=fm-gate-2-control GATE_FILTER="-i 'awilix-release-tier-implicit'" \
  bash official/vm/run-set-v1.sbatch 2>&1 | tee -a "$G_OUT"

step "gate: checks"
python3 official/vm/check-serving.py "$OLOG" "$S0" "$R0" --need-keepalive; SERVING=$?
python3 - "$G_OUT" "$REPO/results/official" <<'PY'; TRIALS=$?
import json, re, sys
gout, res = sys.argv[1], sys.argv[2]
bad = []
log = open(gout, errors="replace").read()
if "NO_VALID_MEMORY" in log: bad.append("generation not valid")
rounds = re.findall(r"round 1: (\d+) trial\(s\) with no reward set aside", log)
print("first-round no-reward counts:", rounds)
if len(rounds) != 2 or any(n != "0" for n in rounds): bad.append("trials without reward on first round")
for job, n in {"fm-gate-2-mem": 2, "fm-gate-2-control": 1}.items():
    try:
        rows = [json.loads(l) for l in open(f"{res}/summary-{job}.jsonl")]
    except FileNotFoundError:
        bad.append(f"{job}: no summary"); continue
    for r in rows:
        print(f"{job}: {r.get('task')} valid={r.get('valid')} reward={r.get('reward')} model_unavailable={r.get('model_unavailable')} judge={r.get('judge_status')}")
    if len(rows) != n: bad.append(f"{job}: {len(rows)} trials, expected {n}")
    bad += [f"{job}: invalid trial"] * any(not r.get("valid") for r in rows)
    bad += [f"{job}: model_unavailable"] * any(r.get("model_unavailable") for r in rows)
    bad += [f"{job}: APEX judge not completed"] * any("apex" in str(r.get("task")) and r.get("judge_status") != "completed" for r in rows)
print("TRIALS:", "ok" if not bad else "FAIL: " + "; ".join(bad))
sys.exit(1 if bad else 0)
PY
if [ "$SERVING" = 0 ] && [ "$TRIALS" = 0 ]; then step "GATE_PASSED"; date > official/vm/GATE_PASSED; else fail "checks failed (see above)"; fi
exit 0
