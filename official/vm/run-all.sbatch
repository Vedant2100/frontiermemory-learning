#!/bin/bash
# The whole counted study in one allocation, so the GPUs are never released between sets (on Nov 3 another user took a node in a 2-minute gap).
# Order fixed by preregistration v2: APEX judge smoke (not counted, stops everything if the judge fails), control, run1, run2, run3.
# Safe to resubmit: finished trials are kept and generation is skipped when a valid memory exists. Each finished set stays finished.
#SBATCH --job-name=fm-serial
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu02
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=12
#SBATCH --mem=64G
#SBATCH --time=14-00:00:00
#SBATCH --output=official/logs/set-%j.log
REPO=$PWD
run() { SET=$1 SMOKE=${2:-0} bash official/vm/run-set.sbatch; }
gpus_free() { for _ in $(seq 1 12); do u=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | sort -n | tail -1); [ "$u" -lt 1000 ] && return 0; pkill -u "$USER" -x ollama; sleep 5; done; echo "GPU_NOT_RELEASED_FAILED"; return 1; }

if [ ! -f "$REPO/results/official/summary-fm-smoke-apex.jsonl" ]; then
  run control apex || { echo "APEX_SMOKE_FAILED"; exit 1; }
fi
python3 - "$REPO/results/official/summary-fm-smoke-apex.jsonl" <<'PY' || { echo "APEX_JUDGE_FAILED"; exit 1; }
import json, sys
rows = [json.loads(line) for line in open(sys.argv[1])]
assert rows and all(r.get("judge_status") == "completed" and r.get("valid") for r in rows), rows
print("APEX_JUDGE_OK", len(rows))
PY
for s in control run1 run2 run3; do
  gpus_free || exit 1
  [ -f "$REPO/results/official/summary-fm-tasks-$s.jsonl" ] && ! grep -q '"valid": false\|"finished": false' "$REPO/results/official/summary-fm-tasks-$s.jsonl" && { echo "=== $s: already complete"; continue; }
  run "$s" || { echo "SET_FAILED_$s"; exit 1; }
  ( cd "$REPO" && python3 -I scripts/analyze_official.py --dir results/official 2>&1 | grep -E '"flags"|no reward|judge failed|expected|attempts differ|tasks, expected' | cut -c1-170 )
done
echo "ALL_SETS_DONE"
