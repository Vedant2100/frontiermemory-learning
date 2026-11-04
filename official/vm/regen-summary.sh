#!/bin/bash
# Regenerate one set's summary with the current fm_local/set_tools.py, inside the running job's VM. Read-only on trials.
# Usage: srun --jobid=<running job> --overlap -n1 -c1 --mem=200M bash official/vm/regen-summary.sh fm-tasks-control
set -euo pipefail
JOB=${1:?job name, e.g. fm-tasks-control}
REPO=/home/csgrad/vbork001/frontiermemory-experiment-20261024
Q=$(pgrep -u "$USER" -f qemu-kvm | head -1); [ -n "$Q" ] || { echo "no VM running in this allocation"; exit 1; }
P=$(tr '\0' ' ' </proc/$Q/cmdline | grep -oE "hostfwd=tcp:127.0.0.1:[0-9]+" | grep -oE "[0-9]+$")
O=(-i /scratch/$USER/fm-vm/id -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)
scp "${O[@]}" -P "$P" -q "$REPO/official/fm_local/set_tools.py" fm@127.0.0.1:regen_set_tools.py
ssh "${O[@]}" -p "$P" fm@127.0.0.1 "cd ~/official/frontiermemory && export PATH=\$PWD/.venv/bin:\$PATH && sudo -E env PATH=\$PATH python3 ~/regen_set_tools.py summary jobs/$JOB > ~/summary-$JOB.regen.jsonl && wc -l < ~/summary-$JOB.regen.jsonl"
scp "${O[@]}" -P "$P" -q "fm@127.0.0.1:summary-$JOB.regen.jsonl" "$REPO/results/official/summary-$JOB.jsonl"
echo "regenerated results/official/summary-$JOB.jsonl"
