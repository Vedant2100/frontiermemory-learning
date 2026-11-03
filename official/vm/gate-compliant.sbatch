#!/bin/bash
# Gate step 2 (protocol v4), counted for nothing: full-run settings on Word2Vec. Generation on the whole corpus under the real
# 6-hour limit, check-memory, Word2Vec with and without that memory, score, bundle, effort audit from request bodies (kept local, then deleted).
#SBATCH --job-name=fm-serial
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu02
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=12
#SBATCH --mem=64G
#SBATCH --time=09:00:00
#SBATCH --output=official/logs/gate-compliant-%j.log
REPO=$PWD; source official/vm/lib.sh
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $*"; }
MODEL=qwen3.8:27b-mtp-q4_K_M; PORT=$(free_port); OLOG=$ROOT/ollama-$SLURM_JOB_ID; mkdir -p "$OLOG/tmp"
apptainer exec --fakeroot --nv --bind /home/csgrad/vbork001/shared-mem-gov-pilot/models:/models --bind "$OLOG:/ollama-logs" \
  --env OLLAMA_MODELS=/models --env OLLAMA_HOST=127.0.0.1:$PORT --env OLLAMA_CONTEXT_LENGTH=262144 --env OLLAMA_KEEP_ALIVE=30m \
  --env OLLAMA_MAX_LOADED_MODELS=1 --env OLLAMA_NUM_PARALLEL=1 --env OLLAMA_DEBUG_LOG_REQUESTS=true --env TMPDIR=/ollama-logs/tmp \
  "$REPO/containers/ollama.sif" ollama serve >>"$OLOG/server.log" 2>&1 & OLLAMA_PID=$!
for _ in $(seq 1 60); do curl -fs -m 3 "http://127.0.0.1:$PORT/api/version" >/dev/null && break; sleep 2; done
vm_boot 8 32G || exit 1
"${SSH[@]}" 'mkdir -p ~/official; rm -rf ~/official/frontiermemory/jobs/compliant-*'; "${SCP[@]}" "$REPO/official/fm_local" fm@127.0.0.1:official/
ENV="cd ~/official/frontiermemory; export PATH=\$PWD/.venv/bin:\$PATH PYTHONPATH=\$HOME/official FM_LOCAL_BASE_URL=http://10.0.2.2:$PORT/v1 OPENAI_API_KEY=local-placeholder; unset OPENAI_BASE_URL"
H="sudo env PATH=\$PATH PYTHONPATH=\$PYTHONPATH FM_LOCAL_BASE_URL=\$FM_LOCAL_BASE_URL OPENAI_API_KEY=\$OPENAI_API_KEY"
COMMON="-m openai/$MODEL -e docker --allow-host 10.0.2.2"

audit() { python3 - "$OLOG/tmp" <<'PY'
import collections,glob,json,os,sys
vals=collections.Counter(); n=0
for root,_,fs in os.walk(sys.argv[1]):
    for f in fs:
        try: d=json.load(open(os.path.join(root,f)))
        except Exception: continue
        if not isinstance(d,dict) or "model" not in d: continue
        n+=1; r=d.get("reasoning") or {}
        vals[("effort",r.get("effort") if isinstance(r,dict) else r)]+=1; vals[("think",d.get("think"))]+=1; vals[("max_output_tokens",d.get("max_output_tokens"))]+=1
print("request bodies",n,dict(vals))
PY
}

step "generation: whole corpus v1.1, real 6-hour limit"
"${SSH[@]}" "$ENV; $H frontier-memory generate-memory --corpus data/corpus/v1.1 --harness fm_local.hermes_local:LocalHermesLearn $COMMON --ak reasoning_effort=max --job-name compliant-gen --jobs-dir jobs 2>&1 | grep -vE '^[┏┡│└╭╰]|^$' | tail -6 | cut -c1-170; sudo chown -R fm:fm jobs/compliant-gen; d=\$(ls -d jobs/compliant-gen/*__* | head -1); python3 -c \"
import json,sys;r=json.load(open(sys.argv[1]));e=r.get('exception_info') or {};print('exception',e.get('exception_type'),str(e.get('exception_message'))[:200]);print('agent',(r.get('agent_execution') or {}).get('started_at','')[11:19],(r.get('agent_execution') or {}).get('finished_at','')[11:19],'verifier',(r.get('verifier_result') or {}).get('rewards'))\" \$d/result.json; [ -f \$d/agent/hermes-result.json ] && python3 -c \"
import json,sys;h=json.load(open(sys.argv[1]));print({k:(v if not isinstance(v,(list,str)) or k in ('status',) else len(v)) for k,v in h.items()})\" \$d/agent/hermes-result.json | cut -c1-500; find \$d/artifacts/memory -type f 2>/dev/null | wc -l; du -sh \$d/artifacts/memory 2>/dev/null; frontier-memory check-memory jobs/compliant-gen 2>&1 | tail -8 | cut -c1-150"
step "effort audit, generation"; audit

step "Word2Vec without memory, 3 attempts"
"${SSH[@]}" "$ENV; $H frontier-memory run-tasks --harness fm_local.hermes_local:LocalHermes $COMMON --tasks data/tasks-fm -k 3 --effort max --job-name compliant-w2v-nomem --jobs-dir jobs -- -i 'build-word2vec*' 2>&1 | tail -1 | cut -c1-120; sudo chown -R fm:fm jobs/compliant-w2v-nomem; frontier-memory score jobs/compliant-w2v-nomem 2>&1 | tail -3 | cut -c1-120"

step "Word2Vec with the generated memory, 3 attempts, if a memory exists"
"${SSH[@]}" "$ENV; if frontier-memory check-memory jobs/compliant-gen >/dev/null 2>&1; then $H frontier-memory run-tasks --harness fm_local.hermes_local:LocalHermes $COMMON --tasks data/tasks-fm -k 3 --effort max --memory jobs/compliant-gen --job-name compliant-w2v-mem --jobs-dir jobs -- -i 'build-word2vec*' 2>&1 | tail -1 | cut -c1-120; sudo chown -R fm:fm jobs/compliant-w2v-mem; frontier-memory score jobs/compliant-w2v-mem 2>&1 | tail -3 | cut -c1-120; frontier-memory bundle --memory-job jobs/compliant-gen --task-job jobs/compliant-w2v-mem --out compliant-bundle.tar.gz 2>&1 | tail -18 | cut -c1-170; else echo NO_VALID_MEMORY; fi"
step "effort audit, all"; audit; grep -cE "POST +\"/v1/responses\"" "$OLOG/server.log"; grep -E "\| +[0-9]{3} \|" "$OLOG/server.log" | grep -oE "\| +[0-9]{3} \|" | sort | uniq -c; grep -oE "truncated = [0-9]+" "$OLOG/server.log" | sort | uniq -c
"${SSH[@]}" 'df -h / | tail -1'
kill $OLLAMA_PID 2>/dev/null; rm -rf "$OLOG/tmp"
step "GATE_COMPLIANT_DONE"
