#!/bin/bash
# CPU-only reference validation for all 15 pinned tasks in the private cluster2 Docker guest.
set -Eeuo pipefail
REPO=$(pwd -P)
[ "$REPO" = "$(realpath "$HOME/frontiermemory-cluster2")" ] || { echo WRONG_WORKTREE; exit 1; }
: "${SLURM_JOB_ID:?Set a unique cluster2 run id}"
[[ "$SLURM_JOB_ID" =~ ^c2-[A-Za-z0-9_-]+$ ]] || { echo BAD_RUN_ID; exit 1; }
source official/vm/lib-cluster2.sh
bash official/vm/check-updates-cluster2.sh
acquire_study_lock
EXPECTED_MODEL=22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643
EXPECTED_CORPUS=19346a3e46b022ed1def552f8e4f4c50030cefd3250a7a8e10676b46b370b763
MODEL_MANIFEST="$ROOT/models/manifests/registry.ollama.ai/library/qwen3.8/27b-mtp-q4_K_M"
CORPUS_MANIFEST="$REPO/data/corpus/v1.1/SHA256SUMS"
[[ "$(sha256sum "$MODEL_MANIFEST" | cut -d' ' -f1)" = "$EXPECTED_MODEL" ]] || { echo MODEL_DIGEST_MISMATCH; exit 1; }
[[ "$(sha256sum "$CORPUS_MANIFEST" | cut -d' ' -f1)" = "$EXPECTED_CORPUS" ]] || { echo CORPUS_MANIFEST_MISMATCH; exit 1; }
KEYFILE="$HOME/.config/frontiermemory/anthropic-api-key"
[ -s "$KEYFILE" ] || { echo JUDGE_KEY_MISSING; exit 1; }
JOB="oracle-all-$SLURM_JOB_ID"
OUT="$REPO/results/official-cluster2/reference-cluster2.json"
mkdir -p "$REPO/results/official-cluster2"
[ ! -e "$OUT" ] || { echo REFERENCE_RECEIPT_EXISTS; exit 1; }
used_kb=$(du -sk "$ROOT" | cut -f1); available_kb=$(df -Pk "$ROOT" | awk 'NR==2 {print $4}')
echo "DISK_STATE used_kib=$used_kb available_kib=$available_kb"
[[ "$used_kb" =~ ^[0-9]+$ && "$available_kb" =~ ^[0-9]+$ ]] &&
  ((used_kb < 145 * 1024 * 1024 && available_kb >= 25 * 1024 * 1024)) || { echo DISK_PREFLIGHT_FAILED; exit 1; }

vm_boot 8 32G
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
watch_disk & watcher=$!
cleanup_oracle() {
  kill "$watcher" 2>/dev/null || true
  wait "$watcher" 2>/dev/null || true
  if [ "${C2_VM_LOCKED:-0}" = 1 ]; then vm_stop; fi
}
trap cleanup_oracle EXIT

G 'grep -q "\"enabled\":false" /etc/docker/daemon.json && sudo docker image inspect fm-w2v-cache >/dev/null'
G 'rm -f ~/.judge-key'
"${SCP[@]}" "$REPO/official/fm_local" fm@127.0.0.1:official/
G 'umask 077; cat > ~/.judge-key' < "$KEYFILE"
G 'for i in 1 2 3 4 5 6; do if sudo docker pull -q '"$PROBE_IMAGE"' >/dev/null; then break; fi; sleep 20; done; sudo docker image inspect '"$PROBE_IMAGE"' >/dev/null'
G "cd ~/official/frontiermemory; test ! -e jobs/$JOB; timeout 21600 sudo env PATH=\$PWD/.venv/bin:\$PATH bash \$HOME/official/fm_local/with_judge_key.sh harbor run -p data/tasks-fm -a oracle -e docker -n 2 --ve GRADING_MODEL=anthropic/claude-opus-5-5 --ve 'ANTHROPIC_API_KEY=\${JUDGE_ANTHROPIC_KEY}' --jobs-dir jobs --job-name $JOB -y > /tmp/$JOB.log 2>&1"
G "cd ~/official/frontiermemory; sudo chown -R fm:fm jobs/$JOB; found=\$(sudo grep -ralF -f ~/.judge-key jobs/$JOB 2>/dev/null || true); leaks=\$(printf '%s\\n' \"\$found\" | sed '/^$/d' | wc -l); [ \"\$leaks\" -eq 0 ] || { echo ORACLE_KEY_LEAK; exit 1; }; python3 - '$JOB' <<'PY'
import collections, json, math, subprocess, sys
from pathlib import Path
job = Path('jobs') / sys.argv[1]
want = {
 'apex-brightpath-market-share': 1.0, 'apex-brightpath-seat-surplus': 1.0,
 'apex-eurogrid-curtailment': 0.8333,
 'automationbench-marketing-content-gap-analysis': 1.0,
 'automationbench-sales-chatgpt-proposal-customization': 1.0,
 'automationbench-sales-partnership-contract': 1.0,
 'awilix-release-tier-explicit': 1.0, 'awilix-release-tier-implicit': 1.0,
 'build-word2vec-pipeline': 1.0, 'cattrs-compositional-changelog': 0.0,
 'cookie-store-compositional-changelog': 0.0,
 'customer-delivery-contextual-preferences': 1.0,
 'dapt-intrusion-detection-workflow-learning': 1.0,
 'enterpriseops-csm-26d1b04a': 0.0, 'enterpriseops-teams-2725d17f': 0.0,
}
files = sorted(job.glob('*/result.json'))
rows = []
counts = collections.Counter()
bad = 0
for path in files:
    result = json.loads(path.read_text())
    task = str(result.get('task_name', '')).split('/')[-1]
    counts[task] += 1
    reward = ((result.get('verifier_result') or {}).get('rewards') or {}).get('reward')
    exception = (result.get('exception_info') or {}).get('exception_type')
    grade = path.parent / 'verifier' / 'grade_details.json'
    judge = json.loads(grade.read_text()).get('grading_run_status') if grade.exists() else None
    ok = task in want and isinstance(reward, (int, float)) and not isinstance(reward, bool) and math.isfinite(reward)
    ok = ok and abs(float(reward) - want.get(task, 999)) < 0.01 and exception is None
    if task.startswith('apex-'):
        ok = ok and judge == 'completed'
    bad += not bool(ok)
    rows.append({'task': task, 'reward': reward, 'judge_completed': judge == 'completed' if task.startswith('apex-') else None})
bad += len(files) != len(want) or counts != collections.Counter({t: 1 for t in want})
tools_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
task_manifest_sha256 = __import__('hashlib').sha256(Path('tasks.json').read_bytes()).hexdigest()
try:
    harbor_bin = Path.cwd() / '.venv' / 'bin' / 'harbor'
    harbor_version = subprocess.check_output([str(harbor_bin), '--version'], text=True, stderr=subprocess.STDOUT).strip()
except subprocess.CalledProcessError:
    harbor_version = 'unavailable'
docker_version = subprocess.check_output(['sudo', 'docker', 'version', '--format', '{{.Server.Version}}'], text=True).strip()
record = {'status': 'pass' if not bad else 'fail', 'oracle_job': sys.argv[1], 'task_count': len(files),
          'tasks': sorted(rows, key=lambda row: row['task']), 'task_release': 'letta-ai/frontier-memory@v1.0',
          'task_manifest_sha256': task_manifest_sha256, 'frontiermemory_commit': tools_commit,
          'harbor_version': harbor_version, 'docker_server_version': docker_version}
Path(f'/home/fm/oracle-summary-{sys.argv[1]}.json').write_text(json.dumps(record, sort_keys=True) + '\\n')
print('ORACLE_TASKS', len(files), 'EXPECTED', len(want), 'MISMATCHES', bad)
print('ORACLE_MATCHES' if not bad else 'ORACLE_MISMATCH')
if bad: raise SystemExit(1)
PY
rm -f /tmp/$JOB.log"
"${SCP[@]}" "fm@127.0.0.1:oracle-summary-$JOB.json" "$OUT"
python3 - "$OUT" "$EXPECTED_MODEL" "$EXPECTED_CORPUS" "$(git rev-parse HEAD)" <<'PY'
import json, os, sys, tempfile
from pathlib import Path
p = Path(sys.argv[1]); record = json.loads(p.read_text())
if record.get('status') != 'pass' or record.get('task_count') != 15:
    raise SystemExit('REFERENCE_CHECK_FAILED')
record.update(model_manifest_sha256=sys.argv[2], corpus_manifest_sha256=sys.argv[3], cluster2_commit=sys.argv[4])
fd, name = tempfile.mkstemp(dir=p.parent, prefix='.reference-cluster2-')
with os.fdopen(fd, 'w') as out:
    json.dump(record, out, sort_keys=True)
    out.write('\n')
os.chmod(name, 0o600)
os.replace(name, p)
print('REFERENCE_CHECK_OK tasks=15; expected scores matched; no content copied')
PY
G 'sudo docker system df | cut -c1-80; df -h / | tail -1; rm -f ~/.judge-key'
cleanup_oracle
trap - EXIT - USR1
echo ORACLE_ALL_CLUSTER2_OK
