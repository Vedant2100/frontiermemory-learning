#!/bin/bash
# Run one full uncounted gate for Hermes, Codex, or Claude Code.
set -Eeuo pipefail
REPO=$(realpath "$HOME/frontiermemory-cluster2"); cd "$REPO"
[[ "$(git branch --show-current)" = cluster2 ]] || { echo WRONG_BRANCH; exit 1; }
TASK_HARNESS=${TASK_HARNESS:-hermes}
case "$TASK_HARNESS" in hermes|codex|claude-code) ;; *) echo BAD_GATE_HARNESS; exit 2 ;; esac
CLAUDE_PREFLIGHT=0
[ "$TASK_HARNESS" != claude-code ] || CLAUDE_PREFLIGHT=1
HARNESS_EGRESS_PREFLIGHT=0
NETWORK_PROBE_PREFLIGHT=1
[[ "$TASK_HARNESS" != codex && "$TASK_HARNESS" != claude-code ]] || HARNESS_EGRESS_PREFLIGHT=1
if [ "$TASK_HARNESS" = claude-code ]; then GATE_SLUG=CLAUDE_CODE; EXPECTED_ROUTE=/v1/messages
else GATE_SLUG=$(printf '%s' "$TASK_HARNESS" | tr '[:lower:]-' '[:upper:]_'); EXPECTED_ROUTE=/v1/responses; fi
SLURM_JOB_ID=${SLURM_JOB_ID:-c2-gate-$TASK_HARNESS-$(date +%m%d%H%M)}
[[ "$SLURM_JOB_ID" =~ ^c2-[A-Za-z0-9_-]+$ ]] || { echo BAD_RUN_ID; exit 1; }
source official/vm/lib-cluster2.sh
bash official/vm/check-updates-cluster2.sh || exit 1
python3 scripts/validate_effort_check_cluster2.py results/effort-check-cluster2.json || { echo U5_EFFORT_CHECK_REQUIRED_BEFORE_GATE; exit 1; }
acquire_study_lock || exit 1
[ -z "$(git status --porcelain)" ] || { echo WORKTREE_NOT_CLEAN; exit 1; }
EXPECTED_MODEL=22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643
EXPECTED_CORPUS=19346a3e46b022ed1def552f8e4f4c50030cefd3250a7a8e10676b46b370b763
MODEL_MANIFEST="$ROOT/models/manifests/registry.ollama.ai/library/qwen3.8/27b-mtp-q4_K_M"
CORPUS_MANIFEST="$REPO/data/corpus/v1.1/SHA256SUMS"
[[ "$(sha256sum "$MODEL_MANIFEST" | cut -d' ' -f1)" = "$EXPECTED_MODEL" ]] || { echo MODEL_DIGEST_MISMATCH; exit 1; }
[[ "$(sha256sum "$CORPUS_MANIFEST" | cut -d' ' -f1)" = "$EXPECTED_CORPUS" ]] || { echo CORPUS_MANIFEST_MISMATCH; exit 1; }
REF="$REPO/results/official-cluster2/reference-cluster2.json"
python3 - "$REF" "$EXPECTED_MODEL" "$EXPECTED_CORPUS" "$(git rev-parse HEAD)" <<'PY'
import json, subprocess, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
if r.get('status') != 'pass' or r.get('task_count') != 15 or len(r.get('tasks', [])) != 15 or r.get('model_manifest_sha256') != sys.argv[2] or r.get('corpus_manifest_sha256') != sys.argv[3]: raise SystemExit('REFERENCE_RECEIPT_INVALID')
subprocess.run(['git', 'merge-base', '--is-ancestor', r['cluster2_commit'], sys.argv[4]], check=True)
print('REFERENCE_RECEIPT_OK tasks=15')
PY
OLOG="$ROOT/ollama-$SLURM_JOB_ID"; G_OUT="$REPO/official/logs/cluster2/gate-$SLURM_JOB_ID.log"
GATE_RECEIPT="$REPO/results/official-cluster2/gate-receipt-$TASK_HARNESS-$SLURM_JOB_ID.json"
RESULTS="$REPO/results/official-cluster2/$SLURM_JOB_ID"
PASSED="official/vm/GATE_PASSED_${GATE_SLUG}_CLUSTER2"; FAILED="official/vm/GATE_FAILED_${GATE_SLUG}_CLUSTER2"
[ ! -e "$OLOG" ] && [ ! -e "$G_OUT" ] && [ ! -e "$GATE_RECEIPT" ] || { echo GATE_ID_ALREADY_USED; exit 1; }
mkdir -p "$REPO/official/logs/cluster2" "$REPO/results/official-cluster2" "$RESULTS"
rm -f "$PASSED" "$FAILED"
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $*"; }
fail() { step "GATE_FAILED: $*"; echo "$*" > "$FAILED"; exit 1; }
gpus_free() { for _ in $(seq 1 12); do python3 official/vm/gpu-check-cluster2.py && return 0; sleep 5; done; return 1; }
gpus_free || fail "GPUs not free"
S0=0; R0=0
[ ! -f "$OLOG/server.log" ] || S0=$(wc -l < "$OLOG/server.log")
[ ! -f "$OLOG/relay.log" ] || R0=$(wc -l < "$OLOG/relay.log")
MEM_TASKS="customer-delivery-contextual-preferences apex-eurogrid-curtailment"
MEM_GEN="fm-gen-gate-$TASK_HARNESS-$SLURM_JOB_ID"; MEM_JOB="fm-gate-memory-$TASK_HARNESS-$SLURM_JOB_ID"
CTRL_JOB="fm-gate-control-$TASK_HARNESS-$SLURM_JOB_ID"
step "$TASK_HARNESS gate 1/2: full memory generation, customer delivery and one APEX task"
GATE_TASKS="$MEM_TASKS" GATE_GENJOB="$MEM_GEN" GATE_TASKJOB="$MEM_JOB" GATE_FILTER="-i 'customer-delivery-contextual-preferences' -i 'apex-eurogrid-curtailment'" \
  CLAUDE_MESSAGES_PREFLIGHT="$CLAUDE_PREFLIGHT" HARNESS_EGRESS_PREFLIGHT="$HARNESS_EGRESS_PREFLIGHT" NETWORK_PROBE_PREFLIGHT="$NETWORK_PROBE_PREFLIGHT" TASK_HARNESS="$TASK_HARNESS" MEMORY_SOURCE=generate SET=run1 SMOKE=gate bash official/vm/run-set-cluster2.sh 2>&1 | tee -a "$G_OUT" || fail "memory gate command failed"
gpus_free || fail "GPUs not free after memory gate"
step "$TASK_HARNESS gate 2/2: full-limit no-memory awilix-release-tier-implicit"
GATE_TASKS=awilix-release-tier-implicit GATE_GENJOB=none GATE_TASKJOB="$CTRL_JOB" GATE_FILTER="-i 'awilix-release-tier-implicit'" \
  CLAUDE_MESSAGES_PREFLIGHT=0 HARNESS_EGRESS_PREFLIGHT="$HARNESS_EGRESS_PREFLIGHT" NETWORK_PROBE_PREFLIGHT="$NETWORK_PROBE_PREFLIGHT" TASK_HARNESS="$TASK_HARNESS" MEMORY_SOURCE=none SET=control SMOKE=gate bash official/vm/run-set-cluster2.sh 2>&1 | tee -a "$G_OUT" || fail "control gate command failed"
step "$TASK_HARNESS gate: serving, route, first-round and summary checks"
python3 official/vm/check-serving.py "$OLOG" "$S0" "$R0" --need-keepalive --summaries "$RESULTS" | tee -a "$G_OUT" || fail "serving check failed"
python3 - "$OLOG/relay.log" "$R0" "$EXPECTED_ROUTE" <<'PY' | tee -a "$G_OUT" || fail "wrong or missing model route"
import collections, json, sys
rows = [json.loads(x) for x in open(sys.argv[1]).read().splitlines()[int(sys.argv[2]):]]
routes = collections.Counter(r.get('path') for r in rows if r.get('method') == 'POST')
print('MODEL_POST_ROUTES', dict(routes))
allowed = {sys.argv[3], '/v1/responses', '/api/show'}  # /api/show is Ollama model metadata, not a task-agent route.
if not routes or not routes[sys.argv[3]] or set(routes) - allowed: raise SystemExit('MODEL_ROUTE_MISMATCH')
PY
python3 scripts/validate_set_cluster2.py "$RESULTS/summary-$MEM_JOB.jsonl" --kind memory --tasks $MEM_TASKS --attempts 1 | tee -a "$G_OUT" || fail "memory summary check failed"
python3 scripts/validate_set_cluster2.py "$RESULTS/summary-$CTRL_JOB.jsonl" --kind control --task awilix-release-tier-implicit | tee -a "$G_OUT" || fail "control summary check failed"
python3 - "$G_OUT" <<'PY' | tee -a "$G_OUT" || fail "a gate task required a no-reward rerun"
import re, sys
x = re.findall(r'round 1: (\d+) trial\(s\) with no reward set aside', open(sys.argv[1], errors='replace').read())
print('GATE_FIRST_ROUND_COUNTS', x)
if len(x) != 2 or any(n != '0' for n in x): raise SystemExit(1)
PY
python3 - "$G_OUT" "$GATE_RECEIPT" "$MEM_JOB" "$CTRL_JOB" "$OLOG" "$REF" "$EXPECTED_MODEL" "$EXPECTED_CORPUS" \
  "$(git rev-parse HEAD)" "$(git rev-parse origin/main:HANDOFF-updates.md)" "$TASK_HARNESS" "$EXPECTED_ROUTE" "$SLURM_JOB_ID" <<'PY'
import datetime, hashlib, json, os, sys, tempfile
from pathlib import Path
log, out, mem_job, ctrl_job, olog, ref, model, corpus, commit, handoff, harness, route, runid = sys.argv[1:]
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
base = Path('results/official-cluster2') / runid
def rows(name): return [json.loads(line) for line in (base / f'summary-{name}.jsonl').read_text().splitlines() if line.strip()]
reference = json.loads(Path(ref).read_text()); mem, control = rows(mem_job), rows(ctrl_job)
audits = {job: json.loads((base / f'audit-config-{job}.json').read_text()) for job in (mem_job, ctrl_job)}
memory_access_receipts = {}
for job, kind, trials in ((mem_job, 'memory', mem), (ctrl_job, 'control', control)):
    access_path = base / f'memory-access-{job}.jsonl'
    check_path = base / f'memory-access-check-{job}.json'
    access_check = json.loads(check_path.read_text())
    digest = audits[job].get('memory_sha256')
    if (access_check.get('status') != 'pass' or access_check.get('harness') != harness
            or access_check.get('kind') != kind or access_check.get('trial_count') != len(trials)
            or access_check.get('summary_sha256') != sha(base / f'summary-{job}.jsonl')
            or access_check.get('memory_access_sha256') != sha(access_path)
            or access_check.get('memory_sha256') != (digest[0] if kind == 'memory' and digest else None)):
        raise SystemExit(f'MEMORY_ACCESS_RECEIPT_FAILED job={job}')
    memory_access_receipts[job] = {'report_sha256':sha(access_path), 'check_sha256':sha(check_path)}
network_probes = {}
for job, kind, trials in ((mem_job, 'memory', 2), (ctrl_job, 'control', 1)):
    a = audits[job]
    if (a.get('status') != 'pass' or a.get('harness') != harness or a.get('kind') != kind
            or a.get('trial_count') != trials or a.get('effort') != 'max' or a.get('concurrency') != 1
            or a.get('environment') != 'docker' or a.get('allowed_host_count') != 1
            or a.get('timeout_multiplier') != 1 or a.get('agent_timeout_multiplier') != 1
            or a.get('model_unavailable') != 0):
        raise SystemExit(f'GATE_CONFIG_AUDIT_FAILED job={job}')
    probe_path = base / f'network-probe-{job}.json'
    probe = json.loads(probe_path.read_text())
    expected_hosts = {'10.0.2.2':True,'api.anthropic.com':False,'api.openai.com':False,
                      'example.com':False,'github.com':False}
    expected_policy = 'agent.network_mode=allowlist;agent.allowed_hosts=10.0.2.2'
    manifest_path = base / f'task-copy-manifest-{job}.json'
    manifest = json.loads(manifest_path.read_text())
    if (probe.get('status') != 'pass' or probe.get('harness') != harness
            or probe.get('task') != 'dapt-intrusion-detection-workflow-learning'
            or probe.get('network_policy') != expected_policy
            or probe.get('task_copy_sha256') != a.get('task_copy_sha256')
            or probe.get('checked_hosts') != expected_hosts
            or probe.get('relay_reachable') is not True
            or probe.get('vendor_reachable') != 0 or probe.get('other_reachable') != 0
            or probe.get('checked_host_count') != 5
            or a.get('network_policy') != expected_policy
            or a.get('task_copy_manifest_sha256') != sha(manifest_path)
            or a.get('network_probe_status') != 'pass'
            or a.get('network_probe_receipt_sha256') != sha(probe_path)
            or manifest.get('task_copy_sha256') != a.get('task_copy_sha256')):
        raise SystemExit(f'GATE_NETWORK_PROBE_FAILED job={job}')
    network_probes[job] = sha(probe_path)
if (audits[mem_job].get('task_copy_sha256') != audits[ctrl_job].get('task_copy_sha256')
        or audits[mem_job].get('task_copy_manifest_sha256') != audits[ctrl_job].get('task_copy_manifest_sha256')):
    raise SystemExit('GATE_TASK_COPY_MISMATCH')
if audits[mem_job].get('memory_sha256') != sorted({r.get('memory_sha256') for r in mem}):
    raise SystemExit('GATE_MEMORY_AUDIT_DIGEST_MISMATCH')
relay_rows = [json.loads(x) for x in Path(olog, 'relay.log').read_text().splitlines()]
routes = __import__('collections').Counter(r.get('path') for r in relay_rows if r.get('method') == 'POST')
record = {'status':'pass','gate_job':runid,'harness':harness,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'cluster2_commit':commit,'handoff_blob':handoff,'model':'qwen3.8:27b-mtp-q4_K_M','model_manifest_sha256':model,
 'effort_check_sha256':sha(Path('results/effort-check-cluster2.json')),
 'corpus_manifest_sha256':corpus,'reference_receipt_sha256':sha(ref),'task_release':'letta-ai/frontier-memory@v1.0',
 'frontiermemory_commit':'9af28c2f8210779f442aa36a1d73553630441af5','task_manifest_sha256':reference['task_manifest_sha256'],
 'harbor_version':reference['harbor_version'],'docker_server_version':reference['docker_server_version'],
 'summaries':{mem_job:sha(base/f'summary-{mem_job}.jsonl'),ctrl_job:sha(base/f'summary-{ctrl_job}.jsonl')},
 'task_copy_sha256':audits[mem_job]['task_copy_sha256'],
 'task_copy_manifest_sha256':audits[mem_job]['task_copy_manifest_sha256'],
 'network_policy':audits[mem_job]['network_policy'],
 'memory_access_receipts':memory_access_receipts,
 'config_audits':{job:sha(base/f'audit-config-{job}.json') for job in audits},
 'network_probe_receipts':network_probes,
 'memory_sha256':sorted({r.get('memory_sha256') for r in mem}),'memory_trials':len(mem),'control_trials':len(control),
 'model_post_routes':dict(routes),
 'serving_log_sha256':{'server':sha(Path(olog)/'server.log'),'relay':sha(Path(olog)/'relay.log')},
 'gate_log_sha256':sha(log),'judge':'anthropic/claude-opus-5-5',
 'settings':{
   'model_context_tokens':262144,
   'effort':{job:audits[job]['effort'] for job in audits},
   'concurrency':{job:audits[job]['concurrency'] for job in audits},
   'environment':{job:audits[job]['environment'] for job in audits},
   'allowed_host_count':{job:audits[job]['allowed_host_count'] for job in audits},
   'timeout_multiplier':{job:audits[job]['timeout_multiplier'] for job in audits},
   'agent_timeout_multiplier':{job:audits[job]['agent_timeout_multiplier'] for job in audits}}}
fd, name = tempfile.mkstemp(dir=Path(out).parent, prefix='.gate-receipt-')
with os.fdopen(fd,'w') as f: json.dump(record,f,sort_keys=True); f.write('\n')
os.chmod(name,0o600); os.replace(name,out); print('GATE_RECEIPT_CREATED')
PY
receipt_sha=$(sha256sum "$GATE_RECEIPT" | cut -d' ' -f1)
printf '%s %s\n' "results/official-cluster2/gate-receipt-$TASK_HARNESS-$SLURM_JOB_ID.json" "$receipt_sha" > "$PASSED"
python3 scripts/check_gate_cluster2.py --harness "$TASK_HARNESS" || { rm -f "$PASSED"; fail "gate receipt verification failed"; }
rm -f "$FAILED"
step "$TASK_HARNESS GATE_PASSED receipt_sha256=$receipt_sha"
