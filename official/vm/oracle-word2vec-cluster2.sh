#!/bin/bash
# Uncounted reference check on the public Word2Vec task in the isolated VM.
set -euo pipefail
REPO=$(pwd -P)
[ "$REPO" = "$(realpath "$HOME/frontiermemory-cluster2")" ] || exit 1
: "${SLURM_JOB_ID:?Set a unique cluster2 run id}"
case "$SLURM_JOB_ID" in c2-*[!a-zA-Z0-9_-]*|*[!a-zA-Z0-9_-]*|'') exit 1 ;; c2-*) ;; *) exit 1 ;; esac
source official/vm/lib-cluster2.sh
bash official/vm/check-updates-cluster2.sh
exec 9>"$ROOT/vm.lock"
flock -n 9 || { echo OWN_VM_BUSY; exit 1; }
vm_boot 6 20G
parent=$$
watch_disk() {
  while kill -0 "$parent" 2>/dev/null; do
    local used avail
    used=$(du -sk "$ROOT" | cut -f1) || used=''
    avail=$(df -Pk "$ROOT" | awk 'NR==2 {print $4}') || avail=''
    if ! [[ "$used" =~ ^[0-9]+$ && "$avail" =~ ^[0-9]+$ ]] || ((used >= 145 * 1024 * 1024 || avail < 25 * 1024 * 1024)); then
      echo DISK_GUARD_STOP >&2
      timeout 30 "${SSH[@]}" 'sudo poweroff' 2>/dev/null || true
      kill -USR1 "$parent" 2>/dev/null || true
      return
    fi
    sleep 30
  done
}
trap 'echo DISK_GUARD_STOP >&2; exit 1' USR1
watch_disk & watch=$!
cleanup_oracle() { kill "$watch" 2>/dev/null || true; wait "$watch" 2>/dev/null || true; vm_stop; }
trap cleanup_oracle EXIT
job="oracle-w2v-$SLURM_JOB_ID"
G 'grep -q "\"enabled\":false" /etc/docker/daemon.json && sudo docker image inspect fm-w2v-cache >/dev/null'
G "cd ~/official/frontiermemory; test ! -e jobs/$job; sudo docker pull -q '$PROBE_IMAGE' >/dev/null; timeout 3600 sudo env PATH=\$PWD/.venv/bin:\$PATH harbor run -p data/tasks-fm -a oracle -e docker -n 1 -i 'build-word2vec*' --jobs-dir jobs --job-name '$job' -y > /tmp/$job.log 2>&1"
G "cd ~/official/frontiermemory; sudo python3 - '$job' <<'PY'
import json, sys
from pathlib import Path
job=Path('jobs')/sys.argv[1]
files=list(job.glob('*/result.json'))
if len(files)!=1:
 print('ORACLE_CHECK_FAILED result_count',len(files));sys.exit(1)
r=json.loads(files[0].read_text())
reward=((r.get('verifier_result') or {}).get('rewards') or {}).get('reward')
exception=(r.get('exception_info') or {}).get('exception_type')
print('ORACLE_WORD2VEC reward',reward,'exception',exception)
if reward != 1 or exception:sys.exit(1)
print('ORACLE_WORD2VEC_OK')
PY"
