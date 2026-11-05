#!/bin/bash
set -euo pipefail
RUN_ID=${2:?unique cluster2 test id required}
case "$RUN_ID" in *[!a-zA-Z0-9_-]*|'') echo BAD_RUN_ID; exit 1 ;; esac
cd ~/official/frontiermemory
sudo env PATH=$PWD/.venv/bin:$PATH PYTHONPATH=$HOME/official harbor run -p build/memory-task-v1.1 -a fm_local.slow_probe:SlowProbe -e docker --allow-agent-host 10.0.2.2 --ak "base=http://10.0.2.2:$1" --jobs-dir jobs --job-name slow-probe-test-$RUN_ID -y > /tmp/slow-run-$RUN_ID.log 2>&1
grep -vE '^[┏┡│└╭╰]|^$' /tmp/slow-run-$RUN_ID.log | grep -iE "error|exception|reward|trial" | tail -8 | cut -c1-160
sudo find jobs/slow-probe-test-$RUN_ID -name slow-probe.json -exec cat {} \;
sudo find jobs/slow-probe-test-$RUN_ID -name exception.txt -exec tail -5 {} \;
