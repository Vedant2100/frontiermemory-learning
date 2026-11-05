#!/bin/bash
set -euo pipefail
log=$1
pid_file=$2
p=$(cat "$pid_file")
[[ "$p" =~ ^[0-9]+$ ]]
kill -0 "$p"
echo KEY_AUDIT_WATCHER_ALIVE
kill "$p" 2>/dev/null || true
for _ in $(seq 1 25); do
  kill -0 "$p" 2>/dev/null || break
  sleep 0.2
done
if kill -0 "$p" 2>/dev/null; then
  echo KEY_AUDIT_WATCHER_DID_NOT_STOP
  kill -KILL "$p" 2>/dev/null || true
  exit 1
fi
samples=$(grep -c 'AUDIT_SAMPLE' "$log" || true)
seen=$(sed -n 's/.*AUDIT_DONE cycles=[0-9]* containers_seen=\([0-9]*\).*/\1/p' "$log" | tail -1)
[[ "$seen" =~ ^[0-9]+$ ]] || seen=0
echo "KEY_AUDIT samples=$samples containers_seen=$seen"
(( samples > 0 && seen > 0 )) || { echo KEY_AUDIT_COVERAGE_MISSING; exit 1; }
if grep -q AGENT_KEY_LEAK "$log"; then
  echo AGENT_KEY_LEAK
  exit 1
fi
cut -d' ' -f2- "$log" | sort | uniq -c | sort -rn | sed -n '1,14p' | cut -c1-100
