#!/bin/bash
# Gate step 1 (protocol v4), counted for nothing. Find the context size that fits, then check Qwen drives official Hermes:
# Word2Vec with no memory, a time-limited generation, Word2Vec with that memory. Real judge key is never present here.
#SBATCH --job-name=fm-serial
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu01
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=12
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=official/logs/gate-plumbing-%j.log
REPO=$PWD; source official/vm/lib.sh
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $*"; }
MODEL=qwen3.8:27b-mtp-q4_K_M; PORT=$(free_port); OLOG=$REPO/official/logs/ollama-$SLURM_JOB_ID; mkdir -p "$OLOG/tmp"
serve() {
  apptainer exec --fakeroot --nv --bind /home/csgrad/vbork001/shared-mem-gov-pilot/models:/models --bind "$OLOG:/ollama-logs" \
    --env OLLAMA_MODELS=/models --env OLLAMA_HOST=127.0.0.1:$PORT --env OLLAMA_CONTEXT_LENGTH=$1 --env OLLAMA_KEEP_ALIVE=30m \
    --env OLLAMA_MAX_LOADED_MODELS=1 --env OLLAMA_NUM_PARALLEL=1 --env OLLAMA_DEBUG_LOG_REQUESTS=true --env TMPDIR=/ollama-logs/tmp \
    "$REPO/containers/ollama.sif" ollama serve >>"$OLOG/server.log" 2>&1 & OLLAMA_PID=$!
  for _ in $(seq 1 60); do curl -fs -m 3 "http://127.0.0.1:$PORT/api/version" >/dev/null && return 0; sleep 2; done; return 1
}
step "GPUs"; nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
step "context size: largest that loads fully on GPU"
CTX=0
for c in 262144 131072 98304 65536; do
  serve $c || { echo "server failed at $c"; continue; }
  curl -s -m 600 "http://127.0.0.1:$PORT/api/generate" -d "{\"model\":\"$MODEL\",\"prompt\":\"hi\",\"stream\":false,\"options\":{\"num_predict\":1}}" -o /dev/null
  P=$(curl -s -m 20 "http://127.0.0.1:$PORT/api/ps"); echo "ctx=$c $(echo "$P" | python3 -c 'import json,sys;m=json.load(sys.stdin)["models"];print([(x.get("context_length"),x["size"],x["size_vram"]) for x in m])' 2>/dev/null)"
  FULL=$(echo "$P" | python3 -c 'import json,sys;m=json.load(sys.stdin)["models"];print(int(bool(m) and m[0]["size"]==m[0]["size_vram"]))' 2>/dev/null)
  if [ "$FULL" = 1 ]; then CTX=$c; break; fi
  kill $OLLAMA_PID; wait $OLLAMA_PID 2>/dev/null
done
[ "$CTX" != 0 ] || { echo "NO_CONTEXT_FITS"; exit 1; }
echo "CONTEXT=$CTX"; curl -s "http://127.0.0.1:$PORT/api/show" -d "{\"name\":\"$MODEL\"}" | python3 -c 'import json,sys;d=json.load(sys.stdin);print({k:v for k,v in d.get("model_info",{}).items() if "context_length" in k}, d.get("capabilities"))'

vm_boot 8 32G || exit 1
"${SSH[@]}" 'mkdir -p ~/official'; "${SCP[@]}" "$REPO/official/fm_local" fm@127.0.0.1:official/
ENV="cd ~/official/frontiermemory; export PATH=\$PWD/.venv/bin:\$PATH PYTHONPATH=\$HOME/official FM_LOCAL_BASE_URL=http://10.0.2.2:$PORT/v1 OPENAI_API_KEY=local-placeholder; unset OPENAI_BASE_URL"
H="sudo env PATH=\$PATH PYTHONPATH=\$PYTHONPATH FM_LOCAL_BASE_URL=\$FM_LOCAL_BASE_URL OPENAI_API_KEY=\$OPENAI_API_KEY"  # sudo drops PYTHON* and others even with -E
COMMON="-m openai/$MODEL -e docker --allow-host 10.0.2.2"

step "model reachable from the guest"
"${SSH[@]}" "curl -s -m 30 -o /dev/null -w 'HTTP %{http_code}\n' http://10.0.2.2:$PORT/v1/models"
"${SSH[@]}" "$ENV; $H python -c 'import fm_local.hermes_local as h; print(\"adapter under sudo OK\", h.base_url())'" || { echo ADAPTER_IMPORT_FAILED; exit 1; }

step "Word2Vec, no memory, one attempt"
"${SSH[@]}" "$ENV; $H frontier-memory run-tasks --harness fm_local.hermes_local:LocalHermes $COMMON --tasks data/tasks-fm -k 1 --effort max --job-name gate-w2v-nomem --jobs-dir jobs -- -i 'build-word2vec*' 2>&1 | tail -4 | cut -c1-170; sudo chown -R fm:fm jobs/gate-w2v-nomem; frontier-memory score jobs/gate-w2v-nomem 2>&1 | tail -3 | cut -c1-120"

step "generation, time-limited to 20 minutes (plumbing only, not compliant)"
"${SSH[@]}" "$ENV; $H frontier-memory generate-memory --corpus data/corpus/v1.1 --harness fm_local.hermes_local:LocalHermesLearn $COMMON --ak reasoning_effort=max --job-name gate-gen-short --jobs-dir jobs -- --agent-timeout-multiplier 0.0556 2>&1 | tail -4 | cut -c1-170; sudo chown -R fm:fm jobs/gate-gen-short; find jobs/gate-gen-short -maxdepth 3 -name 'hermes-result.json' -exec python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print({k:d[k] for k in d if k not in (\"messages\",\"trajectory\")}.keys());print(d.get(\"usage\"))' {} \; ; find jobs/gate-gen-short -type d -name memory | head -2; frontier-memory check-memory jobs/gate-gen-short 2>&1 | tail -6 | cut -c1-140"

step "Word2Vec with that memory, if generation produced one"
"${SSH[@]}" "$ENV; $H frontier-memory run-tasks --harness fm_local.hermes_local:LocalHermes $COMMON --tasks data/tasks-fm -k 1 --effort max --memory jobs/gate-gen-short --job-name gate-w2v-mem --jobs-dir jobs -- -i 'build-word2vec*' 2>&1 | tail -4 | cut -c1-170; sudo chown -R fm:fm jobs/gate-w2v-mem; frontier-memory score jobs/gate-w2v-mem 2>&1 | tail -3 | cut -c1-120"

step "evidence: tool calls, errors, effort"
"${SSH[@]}" "cd ~/official/frontiermemory/jobs; for j in gate-w2v-nomem gate-w2v-mem; do for d in \$j/*__*; do [ -d \"\$d\" ] || continue; echo \"## \$d\"; python3 -c \"
import json,sys;d=json.load(open(sys.argv[1]));e=d.get('exception_info') or {};a=d.get('agent_result') or {};print((d.get('verifier_result') or {}).get('rewards'),e.get('exception_type',''),str(e.get('exception_message',''))[:200],{k:a.get(k) for k in ('n_input_tokens','n_output_tokens')})\" \$d/result.json; tail -6 \$d/agent/hermes.txt 2>/dev/null | cut -c1-180; done; done; df -h / | tail -1" 2>&1
grep -oE '"(reasoning|reasoning_effort|effort)":[^,}]{0,40}' "$OLOG/server.log" | sort | uniq -c | sort -rn | head -5
grep -cE "POST +\"?/v1/(responses|chat)" "$OLOG/server.log"; grep -E "POST" "$OLOG/server.log" | grep -oE "/v1/[a-z/]+|/api/[a-z]+" | sort | uniq -c
kill $OLLAMA_PID 2>/dev/null; rm -rf "$OLOG/tmp"
step "done"
