#!/bin/bash
set -euo pipefail
source official/vm/lib-cluster2.sh
vm_boot 6 20G
step 'reference image build, with disk guard'
G 'cd ~/official/frontiermemory; timeout --signal=TERM --kill-after=30s 3600 sudo docker build --progress=plain -t fm-w2v-cache data/tasks/frontier-memory/build-word2vec-pipeline/environment' &
build_pid=$!
( while kill -0 "$build_pid" 2>/dev/null; do used_kb=$(du -sk "$ROOT" | cut -f1); avail_kb=$(df -Pk "$ROOT" | awk 'NR==2 {print $4}'); if (( used_kb >= 145 * 1024 * 1024 || avail_kb < 25 * 1024 * 1024 )); then echo 'DISK_GUARD_STOP'; kill "$build_pid" 2>/dev/null || true; exit; fi; sleep 30; done ) &
watch_pid=$!
set +e
wait "$build_pid"; result=$?
set -e
kill "$watch_pid" 2>/dev/null || true
wait "$watch_pid" 2>/dev/null || true
echo "BUILD_EXIT=$result"
exit "$result"
