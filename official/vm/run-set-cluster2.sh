#!/bin/bash
set -Eeuo pipefail
# One set under preregistration v2. Safe to resubmit after an interruption: finished trials are kept.
#   sbatch --dependency=singleton --export=ALL,SET=control|run1|run2|run3 official/vm/run-set.sbatch
#   SMOKE=1 runs one Word2Vec attempt under a scratch name and also exercises the rerun path. Never counted.
#   SMOKE=gate runs GATE_FILTER's tasks once into GATE_TASKJOB (memory from GATE_GENJOB unless SET=control). Never counted.
#   SMOKE=apex with SET=control runs one APEX attempt, cut off after about 2 minutes, to exercise the judge path. Never counted.
# Agents get a placeholder key. The judge key reaches only verifiers, through a template, so it is never on a command line or in saved configs.
#SBATCH --job-name=fm-serial
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu02
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=12
#SBATCH --mem=64G
#SBATCH --time=4-00:00:00
#SBATCH --output=official/logs/cluster2/set-%j.log
: "${SET:?set a short cluster2 set label}"; SMOKE="${SMOKE:-0}"
[[ "$SET" =~ ^[a-z0-9][a-z0-9-]{0,39}$ ]] || { echo "bad SET"; exit 2; }
case "$SMOKE" in 0|1|gate|apex) ;; *) echo "bad SMOKE"; exit 2 ;; esac
: "${TASK_HARNESS:=hermes}"
NETWORK_PROBE_ONLY="${NETWORK_PROBE_ONLY:-0}"
case "$NETWORK_PROBE_ONLY" in 0|1) ;; *) echo BAD_NETWORK_PROBE_ONLY; exit 2 ;; esac
[ "$NETWORK_PROBE_ONLY" = 0 ] || [ "$SMOKE" = gate ] || { echo NETWORK_PROBE_ONLY_REQUIRES_UNCOUNTED_GATE_MODE; exit 2; }
EXPERIMENT_ARM=""
case "$TASK_HARNESS" in
  hermes) TASK_ADAPTER=fm_local.hermes_local:LocalHermes; TASK_PROVIDER=openai; TASK_AGENT_ARGS="" ;;
  codex) TASK_ADAPTER=fm_local.codex_local:LocalCodex; TASK_PROVIDER=openai; TASK_AGENT_ARGS="" ;;
  claude-code) TASK_ADAPTER=fm_local.claude_code_local:LocalClaudeCode; TASK_PROVIDER=anthropic; TASK_AGENT_ARGS="" ;;
  exposure-none|exposure-all)
    TASK_ADAPTER=fm_local.exposure_hermes:ExposureHermes; TASK_PROVIDER=openai
    EXPERIMENT_ARM=${TASK_HARNESS#exposure-}
    TASK_AGENT_ARGS="--ak exposure=$EXPERIMENT_ARM"
    ;;
  delivery-cue|delivery-scoped|delivery-categorized)
    delivery_mode=${TASK_HARNESS#delivery-}
    case "$delivery_mode" in
      cue) delivery_class=CueHermes ;;
      scoped) delivery_class=ScopedHermes ;;
      categorized) delivery_class=CategorizedHermes ;;
    esac
    EXPERIMENT_ARM=$delivery_mode
    TASK_ADAPTER="fm_local.delivery_hermes:$delivery_class"; TASK_PROVIDER=openai
    TASK_AGENT_ARGS="--ak delivery=$delivery_mode"
    ;;
  *) echo "bad TASK_HARNESS"; exit 2 ;;
esac
if [ "$TASK_HARNESS" = codex ] || [ "$TASK_HARNESS" = claude-code ]; then
  # U3 requires both resolved-config and effective-egress checks before every
  # Codex/Claude task-agent launch, including uncounted gates and counted sets.
  HARNESS_EGRESS_PREFLIGHT=1
else
  HARNESS_EGRESS_PREFLIGHT=${HARNESS_EGRESS_PREFLIGHT:-0}
fi
NETWORK_PROBE_PREFLIGHT=1
REPO=$(pwd -P)
[ "$REPO" = "$(realpath "$HOME/frontiermemory-cluster2")" ] || { echo WRONG_WORKTREE; exit 1; }
: "${SLURM_JOB_ID:?Set a unique cluster2 run id}"
[[ "$SLURM_JOB_ID" =~ ^c2-[A-Za-z0-9_-]+$ ]] || { echo BAD_RUN_ID; exit 1; }
EXPECTED_TASK_COPY_SHA256=""
if [ "$SMOKE" = 0 ] || [ "$SMOKE" = gate ]; then
  EXPECTED_TASK_COPY_SHA256=$(python3 - "$SMOKE" "$TASK_HARNESS" <<'PY'
import hashlib, json, re, sys
from pathlib import Path
mode, current = sys.argv[1:]
root = Path.cwd()
harnesses = ("hermes", "codex", "claude-code")
digests = []
valid_harnesses = set()
for harness in harnesses:
    if mode == "gate" and harness == current:
        continue
    marker = root / f"official/vm/GATE_PASSED_{harness.upper().replace('-', '_')}_CLUSTER2"
    if not marker.is_file():
        continue
    try:
        bits = marker.read_text().split()
        if len(bits) != 2 or not re.fullmatch(r"[0-9a-f]{64}", bits[1]):
            continue
        receipt_path = (root / bits[0]).resolve()
        if not receipt_path.is_relative_to(root) or not receipt_path.is_file():
            continue
        if hashlib.sha256(receipt_path.read_bytes()).hexdigest() != bits[1]:
            continue
        receipt = json.loads(receipt_path.read_text())
        digest = receipt.get("task_copy_sha256")
        if (receipt.get("status") != "pass"
                or receipt.get("network_policy") != "agent.network_mode=allowlist;agent.allowed_hosts=10.0.2.2"
                or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
            continue
        digests.append(digest)
        valid_harnesses.add(harness)
    except (OSError, ValueError, json.JSONDecodeError):
        continue
if mode == "0" and valid_harnesses != set(harnesses):
    raise SystemExit("ALL_RELAY_ONLY_GATES_REQUIRED_BEFORE_COUNTED_LAUNCH")
if len(set(digests)) > 1:
    raise SystemExit("GATE_TASK_COPY_DIGESTS_DISAGREE")
print(digests[0] if digests else "")
PY
  )
fi
source official/vm/lib-cluster2.sh
bash official/vm/check-updates-cluster2.sh || exit 1
if [ "$SMOKE" = gate ]; then
  python3 scripts/validate_effort_check_cluster2.py results/effort-check-cluster2.json || { echo U5_EFFORT_CHECK_REQUIRED_BEFORE_GATE; exit 1; }
fi
acquire_study_lock || exit 1
python3 official/vm/gpu-check-cluster2.py || exit 1
used_kb=$(du -sk "$ROOT" | cut -f1); available_kb=$(df -Pk "$ROOT" | awk 'NR==2 {print $4}')
echo "DISK_STATE used_kib=$used_kb available_kib=$available_kb"
[[ "$used_kb" =~ ^[0-9]+$ && "$available_kb" =~ ^[0-9]+$ ]] &&
  ((used_kb < 145 * 1024 * 1024 && available_kb >= 25 * 1024 * 1024)) || { echo DISK_PREFLIGHT_FAILED; exit 1; }
expected=22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643
manifest="$ROOT/models/manifests/registry.ollama.ai/library/qwen3.8/27b-mtp-q4_K_M"
[ "$(sha256sum "$manifest" | cut -d' ' -f1)" = "$expected" ] || { echo MODEL_DIGEST_MISMATCH; exit 1; }
if [ "$SMOKE" = 0 ]; then
  gate_harness=$TASK_HARNESS
  case "$gate_harness" in
    exposure-none|exposure-all|delivery-cue|delivery-scoped|delivery-categorized) gate_harness=hermes ;;
  esac
  python3 scripts/check_gate_cluster2.py --harness "$gate_harness" --require-prereg
fi
[ -s "$HOME/.config/frontiermemory/anthropic-api-key" ] || { echo JUDGE_KEY_MISSING; exit 1; }
MODEL=qwen3.8:27b-mtp-q4_K_M; JUDGE=anthropic/claude-opus-5-5
KEY_AUDIT_LOG="key-audit-$SLURM_JOB_ID-$SET.log"
KEY_AUDIT_PID="key-audit-$SLURM_JOB_ID-$SET.pid"
cleanup_c2() {
  kill "${DISK_WATCH_PID:-}" 2>/dev/null || true
  wait "${DISK_WATCH_PID:-}" 2>/dev/null || true
  if [ "${C2_VM_LOCKED:-0}" = 1 ]; then vm_stop; fi
  stop_relay
  stop_model_server
}
trap cleanup_c2 EXIT
model_up "$REPO"
if [ "${CLAUDE_MESSAGES_PREFLIGHT:-0}" = 1 ]; then
  [ "$TASK_HARNESS" = claude-code ] || { echo CLAUDE_PREFLIGHT_WRONG_HARNESS; exit 1; }
  python3 official/vm/probe-messages-cluster2.py "http://127.0.0.1:$RELAY_PORT/v1" "$MODEL" || exit 1
fi
vm_boot 8 40G || { cleanup_c2; exit 1; }
trap cleanup_c2 EXIT
# Stop only this guest and these serving processes if the local disk reaches the study limit.
launcher_pid=$$
disk_guard() {
  while kill -0 "$launcher_pid" 2>/dev/null; do
    local used_kb available_kb
    used_kb=$(du -sk "$ROOT" | cut -f1) || used_kb=''
    available_kb=$(df -Pk "$ROOT" | awk 'NR==2 {print $4}') || available_kb=''
    if ! [[ "$used_kb" =~ ^[0-9]+$ && "$available_kb" =~ ^[0-9]+$ ]] ||
       (( used_kb >= 145 * 1024 * 1024 || available_kb < 25 * 1024 * 1024 )); then
      echo "DISK_GUARD_STOP" >&2
      timeout 30 "${SSH[@]}" 'sudo poweroff' 2>/dev/null || true
      kill "${OLLAMA_PID:-}" "${RELAY_PID:-}" 2>/dev/null || true
      kill -USR1 "$launcher_pid" 2>/dev/null || true
      return
    fi
    sleep 30
  done
}
trap 'echo DISK_GUARD_STOP >&2; exit 1' USR1
disk_guard & DISK_WATCH_PID=$!
G 'grep -q "\"enabled\":false" /etc/docker/daemon.json' || { echo "BUILD_CACHE_GC_NOT_OFF"; exit 1; }
G 'cd ~/official/frontiermemory/data/corpus/v1.1; test "$(sha256sum SHA256SUMS | cut -d" " -f1)" = 19346a3e46b022ed1def552f8e4f4c50030cefd3250a7a8e10676b46b370b763; sha256sum -c SHA256SUMS >/dev/null 2>&1; echo GUEST_CORPUS_CHECK_OK'
G 'sudo docker ps -aq | xargs -r sudo docker rm -f >/dev/null 2>&1; sudo docker network prune -f >/dev/null 2>&1; for i in 1 2 3 4 5 6; do sudo docker pull -q '"$PROBE_IMAGE"' >/dev/null && break; sleep 20; done; sudo docker image inspect '"$PROBE_IMAGE"' >/dev/null' || { echo "PROBE_IMAGE_MISSING"; exit 1; }
G 'sudo docker tag '"$PROBE_IMAGE"' '"$PROBE_IMAGE_TAG"' >/dev/null; sudo docker image inspect '"$PROBE_IMAGE_TAG"' >/dev/null' || { echo "PROBE_IMAGE_ALIAS_MISSING"; exit 1; }
G 'umask 077; cat > ~/.judge-key' < "$HOME/.config/frontiermemory/anthropic-api-key"
"${SCP[@]}" "$REPO/official/fm_local" fm@127.0.0.1:official/
TASK_COPY_EXPECTED_ARG=""
[ -z "$EXPECTED_TASK_COPY_SHA256" ] || TASK_COPY_EXPECTED_ARG="--expected-task-copy-sha256 $EXPECTED_TASK_COPY_SHA256"
G "cd ~/official/frontiermemory; python3 ~/official/fm_local/prepare_cluster2_task_copy.py --source-root data/tasks-fm --output-root data/tasks-fm-cluster2 --manifest data/tasks-fm-cluster2.manifest.json $TASK_COPY_EXPECTED_ARG"
ENV="cd ~/official/frontiermemory; export PATH=\$PWD/.venv/bin:\$PATH PYTHONPATH=\$HOME/official FM_LOCAL_BASE_URL=http://10.0.2.2:$RELAY_PORT/v1 FM_LOCAL_MODEL=$MODEL OPENAI_API_KEY=local-placeholder; unset OPENAI_BASE_URL ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN"
H="sudo env PATH=\$PATH PYTHONPATH=\$PYTHONPATH FM_LOCAL_BASE_URL=\$FM_LOCAL_BASE_URL FM_LOCAL_MODEL=\$FM_LOCAL_MODEL OPENAI_API_KEY=\$OPENAI_API_KEY bash \$HOME/official/fm_local/with_judge_key.sh"
TASK_ENVIRONMENT=docker
TASK_ROOT=data/tasks-fm-cluster2
GEN_COMMON="-m openai/$MODEL -e $TASK_ENVIRONMENT --allow-host 10.0.2.2"
TASK_COMMON="-m $TASK_PROVIDER/$MODEL -e $TASK_ENVIRONMENT --allow-host 10.0.2.2"
if [ "${HARNESS_EGRESS_PREFLIGHT:-0}" = 1 ]; then
  [[ "$TASK_HARNESS" = codex || "$TASK_HARNESS" = claude-code ]] || { echo HARNESS_EGRESS_PREFLIGHT_WRONG_HARNESS; exit 1; }
  [[ "$TASK_ENVIRONMENT" = docker && "$TASK_COMMON" = "-m $TASK_PROVIDER/$MODEL -e $TASK_ENVIRONMENT --allow-host 10.0.2.2" ]] || {
    echo HARNESS_EGRESS_CONFIG_PREFLIGHT_FAILED; exit 1;
  }
  [[ "$ENV" = *"FM_LOCAL_BASE_URL=http://10.0.2.2:$RELAY_PORT/v1"* ]] || { echo HARNESS_RELAY_URL_PREFLIGHT_FAILED; exit 1; }
  if [ "$TASK_HARNESS" = codex ]; then
    grep -q 'OPENAI_BASE_URL.*base_url' "$REPO/official/fm_local/codex_local.py" || { echo CODEX_BASE_URL_OVERRIDE_MISSING; exit 1; }
    grep -q 'OPENAI_API_KEY.*PLACEHOLDER_API_KEY' "$REPO/official/fm_local/codex_local.py" || { echo CODEX_API_KEY_PLACEHOLDER_MISSING; exit 1; }
    ! grep -Eiq 'api\.(openai|anthropic)\.com' "$REPO/official/fm_local/codex_local.py" || { echo CODEX_VENDOR_ENDPOINT_CONFIGURED; exit 1; }
    echo HARNESS_EGRESS_PREFLIGHT_OK harness=codex allowed_hosts=1 relay=1 placeholder_credentials=1
  else
    grep -q 'ANTHROPIC_BASE_URL.*messages_base_url' "$REPO/official/fm_local/claude_code_local.py" || { echo CLAUDE_BASE_URL_OVERRIDE_MISSING; exit 1; }
    grep -q 'ANTHROPIC_API_KEY.*PLACEHOLDER_API_KEY' "$REPO/official/fm_local/claude_code_local.py" || { echo CLAUDE_API_KEY_PLACEHOLDER_MISSING; exit 1; }
    grep -q 'ANTHROPIC_AUTH_TOKEN.*PLACEHOLDER_API_KEY' "$REPO/official/fm_local/claude_code_local.py" || { echo CLAUDE_AUTH_TOKEN_PLACEHOLDER_MISSING; exit 1; }
    ! grep -Eiq 'api\.(openai|anthropic)\.com' "$REPO/official/fm_local/claude_code_local.py" || { echo CLAUDE_VENDOR_ENDPOINT_CONFIGURED; exit 1; }
    echo HARNESS_EGRESS_PREFLIGHT_OK harness=claude-code allowed_hosts=1 relay=1 placeholder_credentials=2
  fi
fi
if [ "$SMOKE" = apex ]; then ATTEMPTS=1; FILTER="-i 'apex-eurogrid*' --agent-timeout-multiplier 0.01"; TASKJOB=fm-smoke-apex
elif [ "$SMOKE" = gate ]; then ATTEMPTS=1; FILTER="${GATE_FILTER:?}"; TASKJOB=${GATE_TASKJOB:?}; GENJOB=${GATE_GENJOB:?}  # restart gate, never counted
elif [ "$SMOKE" = 1 ]; then ATTEMPTS=1; FILTER="-i 'build-word2vec*'"; TASKJOB=fm-smoke-tasks; GENJOB=compliant-gen
else ATTEMPTS=3; FILTER=""; TASKJOB=${TASK_JOB_NAME:-fm-tasks-$SET}; GENJOB=${GEN_JOB_NAME:-fm-gen-$SET}; fi
TASKJOB=${TASK_JOB_NAME:-$TASKJOB}; GENJOB=${GEN_JOB_NAME:-$GENJOB}
if [ "$SMOKE" = gate ]; then RESULTS="$REPO/results/official-cluster2/$SLURM_JOB_ID"
else RESULTS="$REPO/results/official-cluster2/$SLURM_JOB_ID/$TASKJOB"; fi
if [ -z "${MEMORY_SOURCE:-}" ]; then
  if [ "$SET" = control ] && [ "$SMOKE" != 1 ]; then MEMORY_SOURCE=none; else MEMORY_SOURCE=generate; fi
fi
case "$MEMORY_SOURCE" in none|generate|run1) ;; *) echo "bad MEMORY_SOURCE"; exit 2 ;; esac
# One model server, so one trial at a time; agent time limits would otherwise include queueing.
HARBOR_EXTRA="-n 1 $FILTER --ve GRADING_MODEL=$JUDGE --ve 'ANTHROPIC_API_KEY=\${JUDGE_ANTHROPIC_KEY}'"

if [ "$SMOKE" = gate ]; then
  G "test ! -e ~/official/frontiermemory/jobs/$TASKJOB" || { echo GATE_TASK_JOB_NOT_FRESH; exit 1; }
  if [ "$MEMORY_SOURCE" = generate ]; then G "test ! -e ~/official/frontiermemory/jobs/$GENJOB" || { echo GATE_MEMORY_JOB_NOT_FRESH; exit 1; }; fi
fi

G "nohup bash ~/official/fm_local/key_audit.sh >> ~/$KEY_AUDIT_LOG 2>&1 < /dev/null & echo \$! > ~/$KEY_AUDIT_PID"
G 'sudo docker system df | grep -E "Build Cache" | cut -c1-70'

run_tasks() {  # first call starts the job; later calls resume it, keeping finished trials
  local memory="$1"
  if G "[ -f ~/official/frontiermemory/jobs/$TASKJOB/config.json ]"; then
    step "$SET: resuming $TASKJOB"
    G "$ENV; $H harbor jobs resume -p jobs/$TASKJOB 2>&1 | tail -1 | cut -c1-140"
  else
    step "$SET: starting $TASKJOB"
    G "$ENV; $H frontier-memory run-tasks --harness $TASK_ADAPTER $TASK_COMMON --tasks $TASK_ROOT -k $ATTEMPTS --effort max $memory $TASK_AGENT_ARGS --job-name $TASKJOB --jobs-dir jobs -- $HARBOR_EXTRA 2>&1 | tail -1 | cut -c1-140"
  fi
  G "sudo chown -R fm:fm ~/official/frontiermemory/jobs/$TASKJOB"
}

run_network_probe() {
  [ "$NETWORK_PROBE_PREFLIGHT" = 1 ] || { echo NETWORK_PROBE_PREFLIGHT_REQUIRED; return 1; }
  PROBE_TASK=dapt-intrusion-detection-workflow-learning
  PROBE_JOB="c2np-${SLURM_JOB_ID: -12}-${TASK_HARNESS}-${SET}"
  PROBE_LOG="/home/fm/.c2-network-probe-$PROBE_JOB.log"
  PROBE_SAFE="/home/fm/c2-network-probe-$TASKJOB.json"
  PROBE_URLS="urls=[\"http://10.0.2.2:$RELAY_PORT/api/version\",\"https://api.anthropic.com\",\"https://api.openai.com\",\"https://example.com\",\"https://github.com\"]"
  PROBE_RECEIPT="$RESULTS/network-probe.json"
  [ "$SMOKE" != gate ] || PROBE_RECEIPT="$RESULTS/network-probe-$TASKJOB.json"
  mkdir -p "$RESULTS"
  G "$ENV; python3 ~/official/fm_local/check_network_probe.py --check-task-policy --task-config $TASK_ROOT/$PROBE_TASK/task.toml --task-copy-manifest data/tasks-fm-cluster2.manifest.json --task $PROBE_TASK --harness $TASK_HARNESS --relay-url http://10.0.2.2:$RELAY_PORT/api/version"
  G "test ! -e ~/official/frontiermemory/jobs/$PROBE_JOB" || { echo NETWORK_PROBE_JOB_NOT_FRESH; return 1; }
  if ! G "cd ~/official/frontiermemory; sudo -n env HOME=/home/fm PATH=/home/fm/official/frontiermemory/.venv/bin:/usr/local/bin:/usr/bin PYTHONPATH=/home/fm/official FM_LOCAL_BASE_URL=http://10.0.2.2:$RELAY_PORT/v1 FM_LOCAL_MODEL=$MODEL OPENAI_API_KEY=local-placeholder /home/fm/official/frontiermemory/.venv/bin/harbor run -p $TASK_ROOT/$PROBE_TASK -a frontier_memory.agents.probe:NetworkProbe -e docker --allow-agent-host 10.0.2.2 -k 1 --ak '$PROBE_URLS' --jobs-dir jobs --job-name $PROBE_JOB --disable-verification -y > $PROBE_LOG 2>&1"; then
    G "sudo rm -rf ~/official/frontiermemory/jobs/$PROBE_JOB; sudo rm -f $PROBE_LOG"
    echo NETWORK_PROBE_EXECUTION_FAILED
    return 1
  fi
  probe_status=0
  G "cd ~/official/frontiermemory; sudo env HOME=/home/fm PATH=/home/fm/official/frontiermemory/.venv/bin:/usr/local/bin:/usr/bin PYTHONPATH=/home/fm/official /home/fm/official/frontiermemory/.venv/bin/python /home/fm/official/fm_local/check_network_probe.py --task-config $TASK_ROOT/$PROBE_TASK/task.toml --task $PROBE_TASK --harness $TASK_HARNESS --relay-url http://10.0.2.2:$RELAY_PORT/api/version --task-copy-manifest data/tasks-fm-cluster2.manifest.json --raw \"\$(sudo find jobs/$PROBE_JOB -path '*/agent/network-probe.json' -type f -print -quit)\" --receipt $PROBE_SAFE" || probe_status=$?
  G "sudo test -s $PROBE_SAFE" || { G "sudo rm -rf ~/official/frontiermemory/jobs/$PROBE_JOB; sudo rm -f $PROBE_LOG"; echo NETWORK_PROBE_RECEIPT_MISSING; return 1; }
  G "sudo chown fm:fm $PROBE_SAFE"
  "${SCP[@]}" "fm@127.0.0.1:$PROBE_SAFE" "$PROBE_RECEIPT"
  G "sudo rm -rf ~/official/frontiermemory/jobs/$PROBE_JOB; sudo rm -f $PROBE_LOG"
  [ "$probe_status" = 0 ] || { echo NETWORK_PROBE_BLOCKED; return 1; }
  echo NETWORK_PROBE_VALIDATED policy=agent-allowlist relay_only=1
}

run_network_probe || exit 1
if [ "$NETWORK_PROBE_ONLY" = 1 ]; then
  G "rm -f $PROBE_SAFE"
  step "NETWORK_PROBE_ONLY_OK no task-agent task, generation, or counted set launched"
  cleanup_c2
  trap - EXIT
  trap - USR1
  exit 0
fi

MEM=""
case "$MEMORY_SOURCE" in
  none) ;;
  run1)
    GENJOB=${MEMORY_JOB_NAME:-fm-gen-run1}
    EXPECTED_MEMORY=${EXPECTED_MEMORY:?set the validated HM1 memory digest}
    [[ "$EXPECTED_MEMORY" =~ ^[0-9a-f]{64}$ ]] || { echo BAD_EXPECTED_MEMORY; exit 1; }
    G "$ENV; frontier-memory check-memory jobs/$GENJOB >/dev/null 2>&1 && echo MEMORY_CHECK_OK" || { step "$SET: NO_VALID_MEMORY: trials not run"; exit 1; }
    actual_memory=$(G "$ENV; p=\$(find jobs/$GENJOB -path '*/artifacts/memory/MEMORY.md' -print -quit); test -n \"\$p\"; python3 -c 'import sys; from pathlib import Path; from frontier_memory.memory import check_memory; r=check_memory(Path(sys.argv[1])); print(r[\"memory_sha256\"] if r[\"ok\"] else \"INVALID\")' \"\${p%/MEMORY.md}\"")
    [ "$actual_memory" = "$EXPECTED_MEMORY" ] || { echo "HM1_MEMORY_DIGEST_MISMATCH expected=$EXPECTED_MEMORY actual=$actual_memory"; exit 1; }
    MEM="--memory jobs/$GENJOB"
    ;;
  generate)
    if [ "$SMOKE" != 1 ] && ! G "$ENV; frontier-memory check-memory jobs/$GENJOB >/dev/null 2>&1"; then
      step "$SET: fresh generation"
      G "$ENV; [ ! -e jobs/$GENJOB ] || sudo mv jobs/$GENJOB jobs/$GENJOB.failed-\$(date +%s); $H frontier-memory generate-memory --corpus data/corpus/v1.1 --harness fm_local.hermes_local:LocalHermesLearn $GEN_COMMON --ak reasoning_effort=max --job-name $GENJOB --jobs-dir jobs 2>&1 | tail -1 | cut -c1-140; sudo chown -R fm:fm jobs/$GENJOB"
    fi
    G "$ENV; frontier-memory check-memory jobs/$GENJOB >/dev/null 2>&1 && echo MEMORY_CHECK_OK" || { step "$SET: NO_VALID_MEMORY: trials not run"; exit 1; }
    MEM="--memory jobs/$GENJOB"
    ;;
esac

if [ "${HARNESS_EGRESS_PREFLIGHT:-0}" = 1 ]; then
  PREFLIGHT_CONFIG="/home/fm/c2-agent-config-$TASKJOB.json"
  if ! G "$ENV; umask 077; $H frontier-memory run-tasks --harness $TASK_ADAPTER $TASK_COMMON --tasks $TASK_ROOT -k $ATTEMPTS --effort max $MEM $TASK_AGENT_ARGS --job-name $TASKJOB --jobs-dir jobs -- $HARBOR_EXTRA --print-config > $PREFLIGHT_CONFIG 2>&1"; then
    G "rm -f $PREFLIGHT_CONFIG"
    echo HARNESS_EGRESS_CONFIG_PRINT_FAILED
    exit 1
  fi
  G "python3 ~/official/fm_local/check_agent_egress_config.py $PREFLIGHT_CONFIG $TASK_HARNESS $TASK_ENVIRONMENT"
  G "test ! -e ~/official/frontiermemory/jobs/$TASKJOB"
  echo HARNESS_EGRESS_RUNTIME_PREFLIGHT_OK task_jobs=0
fi

if [ "${EXPOSURE_E2E:-0}" = 1 ]; then
  L0=$(wc -l < "$OLOG/server.log" 2>/dev/null || echo 0)
  # The E2E task job is fresh and has one selected task; this check is counts and digest only.
  run_tasks "$MEM"
  first=$(tail -n +"$((L0 + 1))" "$OLOG/server.log" | grep -oE 'task.n_tokens = [0-9]+' | head -1 | grep -oE '[0-9]+$' || true)
  report=$(G "cd ~/official/frontiermemory; p=\$(find jobs/$TASKJOB -name exposure-report.json -print -quit); test -n \"\$p\"; python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); print(json.dumps({k:r.get(k) for k in (\"exposure\",\"memory_sha256\",\"memory_files\",\"memory_bytes\",\"memory_block_shown\",\"skills_index_shown\",\"injected_bytes\",\"injected_tokens_estimate\")}))' \"\$p\"")
  EXPOSURE_REPORT="$report" FIRST_PROMPT_TOKENS="${first:-}" EXPECTED_MEMORY="$EXPECTED_MEMORY" TASK_HARNESS="$TASK_HARNESS" python3 - <<'PY'
import json, os, sys
r = json.loads(os.environ["EXPOSURE_REPORT"])
arm = os.environ["TASK_HARNESS"].removeprefix("exposure-")
expected = os.environ["EXPECTED_MEMORY"]
try: estimate = int(r["injected_tokens_estimate"])
except (KeyError, TypeError, ValueError): raise SystemExit("EXPOSURE_CHECK_FAILED: no injected-token estimate")
try: prompt = int(os.environ["FIRST_PROMPT_TOKENS"])
except ValueError: prompt = None
ok = r.get("exposure") == arm and r.get("memory_sha256") == expected and int(r.get("memory_files") or 0) > 0
if arm == "none":
    ok = ok and estimate == 0 and r.get("memory_block_shown") is False and r.get("skills_index_shown") is False
else:
    ok = ok and estimate > 0 and r.get("memory_block_shown") is True and r.get("skills_index_shown") is True
    ok = ok and prompt is not None and prompt >= estimate
print(f"EXPOSURE_CHECK arm={arm} first_prompt_tokens={prompt if prompt is not None else 'none'} injected_tokens_estimate={estimate} memory_files={r.get('memory_files')} digest_match={r.get('memory_sha256') == expected}")
if not ok: raise SystemExit("EXPOSURE_CHECK_FAILED")
print("EXPOSURE_CHECK_OK")
PY
else
  run_tasks "$MEM"
fi
for round in 1 2 3; do  # official rule: trials with no reward are rerun and not counted
  G "$ENV; sudo install -d -o fm -g fm -m 0700 -- jobs/$TASKJOB.no-reward"
  n=$(G "$ENV; python3 ~/official/fm_local/set_tools.py set-aside jobs/$TASKJOB")
  step "$SET: round $round: $n trial(s) with no reward set aside"
  [ "$n" = 0 ] && break
  run_tasks "$MEM"
done
if [ "$SMOKE" = 1 ]; then
  step "$SET: smoke only: exercise the rerun path by setting the finished trial aside as if it had failed"
  G "$ENV; sudo install -d -o fm -g fm -m 0700 -- jobs/$TASKJOB.smoke-aside; d=\$(ls -d jobs/$TASKJOB/*__* | head -1); mv \$d jobs/$TASKJOB.smoke-aside/"
  run_tasks "$MEM"
fi

step "$SET: score and archive"
G "$ENV; frontier-memory score jobs/$TASKJOB 2>&1 | tail -22 | cut -c1-110; python3 ~/official/fm_local/set_tools.py summary jobs/$TASKJOB $TASK_HARNESS > ~/summary-$TASKJOB.jsonl; wc -l < ~/summary-$TASKJOB.jsonl; python3 -c \"
import collections,json,sys
print('judge status', dict(collections.Counter(json.loads(l).get('judge_status') for l in open(sys.argv[1]))))\" ~/summary-$TASKJOB.jsonl"
if [ "$MEMORY_SOURCE" != none ]; then G "$ENV; frontier-memory bundle --memory-job jobs/$GENJOB --task-job jobs/$TASKJOB --out $TASKJOB-bundle.tar.gz 2>&1 | tail -14 | cut -c1-170"; fi
mkdir -p "$RESULTS"; "${SCP[@]}" "fm@127.0.0.1:summary-$TASKJOB.jsonl" "$RESULTS/"
summary="$RESULTS/summary-$TASKJOB.jsonl"
analysis_summaries="$REPO/results/official-cluster2/$SLURM_JOB_ID/analysis-inputs"
mkdir -p "$analysis_summaries"
summary_flat="$analysis_summaries/summary-$TASKJOB.jsonl"
cp "$summary" "$summary_flat.tmp"
mv "$summary_flat.tmp" "$summary_flat"
"${SCP[@]}" "$REPO/scripts/memory_access.py" fm@127.0.0.1:memory_access.py
if [ "$MEMORY_SOURCE" != none ]; then
  G "cd ~/official/frontiermemory; p=\$(find jobs/$GENJOB -path '*/artifacts/memory/MEMORY.md' -print -quit); test -n \"\$p\"; python3 ~/memory_access.py jobs/$TASKJOB --harness $TASK_HARNESS --arm $SET --memory-dir \"\${p%/MEMORY.md}\" --out ~/memory-access-$TASKJOB.jsonl 2> ~/memory-access-$TASKJOB.summary.json" || { echo MEMORY_ACCESS_FAILED; exit 1; }
else
  G "cd ~/official/frontiermemory; python3 ~/memory_access.py jobs/$TASKJOB --harness $TASK_HARNESS --arm $SET --out ~/memory-access-$TASKJOB.jsonl 2> ~/memory-access-$TASKJOB.summary.json" || { echo MEMORY_ACCESS_FAILED; exit 1; }
fi
"${SCP[@]}" "fm@127.0.0.1:memory-access-$TASKJOB.jsonl" "$RESULTS/"
"${SCP[@]}" "fm@127.0.0.1:memory-access-$TASKJOB.summary.json" "$RESULTS/"
kind=memory
if [ "${EXPOSURE_ARM:-0}" = 1 ]; then kind=exposure
elif [ "$MEMORY_SOURCE" = none ]; then kind=control
fi
python3 scripts/validate_memory_access_cluster2.py "$summary" "$RESULTS/memory-access-$TASKJOB.jsonl" \
  --harness "$TASK_HARNESS" --kind "$kind" --receipt "$RESULTS/memory-access-check-$TASKJOB.json"
measure_arm=""
case "$TASK_HARNESS" in
  exposure-none) measure_arm=none ;;
  exposure-all) measure_arm=all ;;
  delivery-cue) measure_arm=cue ;;
  delivery-scoped) measure_arm=scoped ;;
  delivery-categorized) measure_arm=categorized ;;
  codex|claude-code)
    if [ "$SMOKE" = 0 ]; then
      if [ "$MEMORY_SOURCE" = none ]; then measure_arm=none; else measure_arm=hm; fi
    fi
    ;;
esac
if [ -n "$measure_arm" ]; then
  measure_genjob=$GENJOB
  if { [ "$TASK_HARNESS" = codex ] || [ "$TASK_HARNESS" = claude-code ]; } && [ "$MEMORY_SOURCE" = none ]; then
    measure_genjob=${MEMORY_JOB_NAME:-fm-gen-run1}
  fi
  "${SCP[@]}" "$REPO/scripts/exposure_measure_cluster2.py" fm@127.0.0.1:exposure_measure_cluster2.py
  expected_measure_count=$(wc -l < "$summary")
  G "cd ~/official/frontiermemory; p=\$(find jobs/$measure_genjob -path '*/artifacts/memory/MEMORY.md' -print -quit); test -n \"\$p\"; python3 ~/exposure_measure_cluster2.py jobs/$TASKJOB \"\${p%/MEMORY.md}\" --harness $TASK_HARNESS --arm $measure_arm --expected-count $expected_measure_count --out ~/exposure-measure-$TASKJOB.jsonl" || { echo EXPOSURE_MEASURE_FAILED; exit 1; }
  "${SCP[@]}" "fm@127.0.0.1:exposure-measure-$TASKJOB.jsonl" "$RESULTS/"
  "${SCP[@]}" "fm@127.0.0.1:exposure-measure-$TASKJOB.summary.json" "$RESULTS/"
  python3 scripts/validate_exposure_measure_cluster2.py "$summary" \
    "$RESULTS/exposure-measure-$TASKJOB.jsonl" "$RESULTS/exposure-measure-$TASKJOB.summary.json" \
    --harness "$TASK_HARNESS" --arm "$measure_arm" \
    --receipt "$RESULTS/exposure-measure-check-$TASKJOB.json" || { echo EXPOSURE_MEASURE_VALIDATION_FAILED; exit 1; }
fi
validate=(python3 scripts/validate_set_cluster2.py "$summary" --kind "$kind")
if [ "$SMOKE" = gate ]; then
  : "${GATE_TASKS:?exact task ids required for gate summary validation}"
  read -r -a gate_tasks <<< "$GATE_TASKS"
  validate+=(--tasks "${gate_tasks[@]}" --attempts 1)
elif [ "${EXPOSURE_E2E:-0}" = 1 ] || [ "$SMOKE" = 1 ]; then
  validate+=(--task build-word2vec-pipeline)
elif [ "$SMOKE" = apex ]; then
  validate+=(--task apex-eurogrid-curtailment)
fi
if [ "$MEMORY_SOURCE" = run1 ] || [ "$kind" = exposure ]; then validate+=(--expected-memory "${EXPECTED_MEMORY:?run 1 memory digest required}"); fi
"${validate[@]}"
G "bash ~/official/fm_local/check_key_audit.sh ~/$KEY_AUDIT_LOG ~/$KEY_AUDIT_PID; sudo docker system df | grep -E 'Build Cache' | cut -c1-70; df -h / | tail -1"
"${SCP[@]}" "fm@127.0.0.1:$KEY_AUDIT_LOG" "$RESULTS/"
G "found=\$(sudo grep -ralF -f ~/.judge-key ~/official/frontiermemory/jobs/$TASKJOB 2>/dev/null || true); leaks=\$(printf '%s\\n' \"\$found\" | sed '/^$/d' | wc -l); echo \"saved files holding key: \$leaks\"; [ \"\$leaks\" -eq 0 ]"
"${SCP[@]}" "$REPO/official/vm/audit-set.py" fm@127.0.0.1:audit-set.py
audit_remote="sudo /home/fm/official/frontiermemory/.venv/bin/python /home/fm/audit-set.py jobs/$TASKJOB --harness $TASK_HARNESS --kind $kind --environment $TASK_ENVIRONMENT --attempts $ATTEMPTS"
audit_remote="$audit_remote --task-copy-root $TASK_ROOT --task-copy-manifest data/tasks-fm-cluster2.manifest.json"
if [ "$SMOKE" = gate ]; then audit_remote="$audit_remote --tasks $GATE_TASKS"
elif [ "$SMOKE" = 1 ]; then audit_remote="$audit_remote --tasks build-word2vec-pipeline"
elif [ "$SMOKE" = apex ]; then audit_remote="$audit_remote --tasks apex-eurogrid-curtailment"
fi
if [ "$MEMORY_SOURCE" = run1 ]; then audit_remote="$audit_remote --expected-memory $EXPECTED_MEMORY"; fi
if [ -n "$EXPERIMENT_ARM" ]; then audit_remote="$audit_remote --expected-arm $EXPERIMENT_ARM"; fi
if [ "$NETWORK_PROBE_PREFLIGHT" = 1 ]; then audit_remote="$audit_remote --network-probe-receipt $PROBE_SAFE"; fi
audit_remote="$audit_remote --json-out /home/fm/audit-config-$TASKJOB.json"
if [ "$SMOKE" = 0 ]; then audit_remote="$audit_remote --allow-model-unavailable"; fi
G "cd ~/official/frontiermemory; $audit_remote" > "$RESULTS/audit-$TASKJOB.txt" 2>&1
"${SCP[@]}" "fm@127.0.0.1:/home/fm/audit-config-$TASKJOB.json" "$RESULTS/"
"${SCP[@]}" "fm@127.0.0.1:official/frontiermemory/data/tasks-fm-cluster2.manifest.json" "$RESULTS/task-copy-manifest-$TASKJOB.json"
tail -3 "$RESULTS/audit-$TASKJOB.txt"
if [ "$NETWORK_PROBE_PREFLIGHT" = 1 ]; then G "rm -f $PROBE_SAFE"; fi
cleanup_c2; trap - EXIT; trap - USR1; rm -rf "${OLOG:?}/tmp"
step "$SET: SET_DONE"
