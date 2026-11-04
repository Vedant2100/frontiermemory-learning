#!/bin/bash
# Slow-path test of the relay through Harbor's real egress proxy, inside the held allocation; no GPU used.
#   srun --jobid=<job> --overlap bash official/tests/relay-proxy-test.sh
REPO=/home/csgrad/vbork001/frontiermemory-experiment-20261024
source "$REPO/official/vm/lib.sh"
LOG=$REPO/official/tests/relay-proxy-test.log; : >"$LOG"
SRV_PORT=$(free_port); RELAY_PORT=$(free_port)
python3 "$REPO/official/vm/slow-server.py" "$SRV_PORT" & SRV=$!
python3 "$REPO/official/fm_local/model_relay.py" "$RELAY_PORT" "$SRV_PORT" "$LOG" & RELAY_PID=$!
vm_boot 8 32G || exit 1
"${SCP[@]}" "$REPO/official/fm_local/slow_probe.py" fm@127.0.0.1:official/fm_local/slow_probe.py
"${SCP[@]}" "$REPO/official/tests/guest-slow.sh" fm@127.0.0.1:guest-slow.sh
G "bash guest-slow.sh $RELAY_PORT"
kill $SRV
echo "--- relay log"; cut -c1-200 "$LOG"
