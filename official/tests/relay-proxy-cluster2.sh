#!/bin/bash
# Uncounted synthetic relay check through the real Harbor egress proxy.
set -euo pipefail
REPO=$(realpath "$HOME/frontiermemory-cluster2")
cd "$REPO"
: "${SLURM_JOB_ID:?Set a unique cluster2 run id}"
case "$SLURM_JOB_ID" in c2-*[!a-zA-Z0-9_-]*|*[!a-zA-Z0-9_-]*|'') echo BAD_RUN_ID; exit 1 ;; c2-*) ;; *) echo BAD_RUN_ID; exit 1 ;; esac
source official/vm/lib-cluster2.sh
bash official/vm/check-updates-cluster2.sh || exit 1
LOG="$ROOT/relay-proxy-$SLURM_JOB_ID.log"
[ ! -e "$LOG" ] || { echo TEST_ID_ALREADY_USED; exit 1; }
SRV_PORT=$(free_port); RELAY_PORT=$(free_port)
python3 "$REPO/official/vm/slow-server.py" "$SRV_PORT" >"$ROOT/slow-server-$SLURM_JOB_ID.log" 2>&1 & SRV=$!
trap 'kill "$SRV" 2>/dev/null || true' EXIT
python3 "$REPO/official/fm_local/model_relay.py" "$RELAY_PORT" "$SRV_PORT" "$LOG" >"$ROOT/relay-proxy-$SLURM_JOB_ID.err" 2>&1 & RELAY_PID=$!
if ! vm_boot 8 32G; then kill "$SRV" "$RELAY_PID" 2>/dev/null || true; exit 1; fi
cleanup_relay_test() { vm_stop; kill "$SRV" 2>/dev/null || true; }
trap cleanup_relay_test EXIT
G 'test -d ~/official/frontiermemory/build/memory-task-v1.1' || { echo MEMORY_TASK_NOT_BUILT; exit 1; }
G 'mkdir -p ~/official/fm_local'
"${SCP[@]}" "$REPO/official/fm_local/slow_probe.py" fm@127.0.0.1:official/fm_local/slow_probe.py
"${SCP[@]}" "$REPO/official/tests/guest-slow-cluster2.sh" fm@127.0.0.1:guest-slow-cluster2.sh
G "bash guest-slow-cluster2.sh $RELAY_PORT $SLURM_JOB_ID"
echo 'Relay test log:'
cut -c1-200 "$LOG"
