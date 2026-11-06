#!/bin/bash
# Effort probe (effort_probe.py) on the host GPUs: start the model server as every set does, probe it, stop it.
# No VM, no trials. Output: official/logs and results/official/effort-probe-<job>.txt. Exit status is the probe's.
REPO=${REPO:-$HOME/frontiermemory-experiment-20261024}; cd "$REPO" || exit 1
source official/vm/lib.sh
MODEL=qwen3.8:27b-mtp-q4_K_M
model_up "$REPO" || exit 1
mkdir -p results/official
python3 official/vm/effort_probe.py "$PORT" "$MODEL" | tee "results/official/effort-probe-$SLURM_JOB_ID.txt"; rc=${PIPESTATUS[0]}
kill "$RELAY_PID" "$OLLAMA_PID" 2>/dev/null; pkill -u "$USER" -x ollama; rm -rf "${OLOG:?}/tmp"
exit "$rc"
