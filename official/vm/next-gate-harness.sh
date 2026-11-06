#!/bin/bash
# Full uncounted gate for one swapped task-agent harness (codex or claude), never counted (results/preregistration-arms.md).
# Same parts and pass rule as gate 2 (next-gate-2.sh, D102), through the arm's own derived set script:
#   1. memory (HM run 1's, reused): customer delivery and one APEX task (fm-gate-<h>-mem)
#   2. no memory: awilix-release-tier-implicit to its own full limit, the longest task (D93 rule) (fm-gate-<h>-control)
# PASS needs: serving check ok (check-serving.py, keepalives used), every trial valid with a reward on its first round,
# the APEX judge completed, and the harness's own API path seen at the relay (ARM_API_CHECK). Writes
# official/vm/GATE_PASSED_<H> or GATE_FAILED_<H>. Always exits 0.
#   bash official/vm/next-gate-harness.sh codex|claude
H=${1:?codex or claude}; case "$H" in codex) MEM_ARM=cm; CTRL_ARM=c0 ;; claude) MEM_ARM=km; CTRL_ARM=k0 ;; *) exit 0 ;; esac
UH=$(echo "$H" | tr a-z A-Z)
REPO=$HOME/frontiermemory-experiment-20261024; cd "$REPO" || exit 0
OLOG=/scratch/$USER/fm-vm/ollama-$SLURM_JOB_ID; G_OUT=$REPO/official/logs/gate-$H-$SLURM_JOB_ID.log
rm -f "official/vm/GATE_PASSED_$UH" "official/vm/GATE_FAILED_$UH"
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $*"; }
gpus_free() { for _ in $(seq 1 12); do u=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | sort -n | tail -1); [ "$u" -lt 1000 ] && return 0; pkill -u "$USER" -x ollama; sleep 5; done; return 1; }
fail() { step "GATE_FAILED_$UH: $*"; echo "$*" > "official/vm/GATE_FAILED_$UH"; exit 0; }

S0=$(wc -l < "$OLOG/server.log" 2>/dev/null || echo 0); R0=$(wc -l < "$OLOG/relay.log" 2>/dev/null || echo 0)
gpus_free || fail "GPUs not free"
step "$H gate 1/2: customer delivery and APEX with HM run 1's memory"
SMOKE=gate GATE_GENJOB=fm-gen-run1 GATE_TASKJOB=fm-gate-$H-mem GATE_FILTER="-i 'customer-delivery-contextual-preferences' -i 'apex-eurogrid-curtailment'" \
  bash official/vm/run-arm.sh "$MEM_ARM" 2>&1 | tee -a "$G_OUT"
gpus_free || fail "GPUs not free after part 1"
step "$H gate 2/2: awilix-release-tier-implicit, no memory, full limit"
SMOKE=gate GATE_GENJOB=none GATE_TASKJOB=fm-gate-$H-control GATE_FILTER="-i 'awilix-release-tier-implicit'" \
  bash official/vm/run-arm.sh "$CTRL_ARM" 2>&1 | tee -a "$G_OUT"

step "$H gate: checks"
python3 official/vm/check-serving.py "$OLOG" "$S0" "$R0" --need-keepalive; SERVING=$?
python3 - "$G_OUT" "$REPO/results/official" "$H" <<'PY'; TRIALS=$?
import json, re, sys
gout, res, h = sys.argv[1:4]
bad = []
log = open(gout, errors="replace").read()
if "ARM_CHECK_FAILED" in log: bad.append("arm check failed")
if len(re.findall(r"ARM_API_CHECK path=\S+ requests=[1-9]", log)) != 2: bad.append("harness API path not seen at the relay in both parts")
rounds = re.findall(r"round 1: (\d+) trial\(s\) with no reward set aside", log)
print("first-round no-reward counts:", rounds)
if len(rounds) != 2 or any(n != "0" for n in rounds): bad.append("trials without reward on first round")
for job, n in {f"fm-gate-{h}-mem": 2, f"fm-gate-{h}-control": 1}.items():
    try:
        rows = [json.loads(l) for l in open(f"{res}/summary-{job}.jsonl")]
    except FileNotFoundError:
        bad.append(f"{job}: no summary"); continue
    for r in rows:
        print(f"{job}: {r.get('task')} valid={r.get('valid')} reward={r.get('reward')} judge={r.get('judge_status')}")
    if len(rows) != n: bad.append(f"{job}: {len(rows)} trials, expected {n}")
    bad += [f"{job}: invalid trial"] * any(not r.get("valid") for r in rows)
    bad += [f"{job}: APEX judge not completed"] * any("apex" in str(r.get("task")) and r.get("judge_status") != "completed" for r in rows)
print("TRIALS:", "ok" if not bad else "FAIL: " + "; ".join(bad))
sys.exit(1 if bad else 0)
PY
if [ "$SERVING" = 0 ] && [ "$TRIALS" = 0 ]; then step "GATE_PASSED_$UH"; date > "official/vm/GATE_PASSED_$UH"; else fail "checks failed (see above)"; fi
exit 0
