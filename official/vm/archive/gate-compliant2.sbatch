#!/bin/bash
# Gate step 2, second part, counted for nothing: reuses memory from the compliant generation (305786). Word2Vec with and without it, one trial at a time;
# score, bundle, effort audit; APEX judge and key check.
#SBATCH --job-name=fm-serial
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu02
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=12
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=official/logs/gate-compliant2-%j.log
REPO=$PWD; source official/vm/lib.sh
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $*"; }
MODEL=qwen3.8:27b-mtp-q4_K_M; PORT=$(free_port); OLOG=$ROOT/ollama-$SLURM_JOB_ID; mkdir -p "$OLOG/tmp"
apptainer exec --fakeroot --nv --bind /home/csgrad/vbork001/shared-mem-gov-pilot/models:/models --bind "$OLOG:/ollama-logs" \
  --env OLLAMA_MODELS=/models --env OLLAMA_HOST=127.0.0.1:$PORT --env OLLAMA_CONTEXT_LENGTH=262144 --env OLLAMA_KEEP_ALIVE=30m \
  --env OLLAMA_MAX_LOADED_MODELS=1 --env OLLAMA_NUM_PARALLEL=1 --env OLLAMA_DEBUG_LOG_REQUESTS=true --env TMPDIR=/ollama-logs/tmp \
  "$REPO/containers/ollama.sif" ollama serve >>"$OLOG/server.log" 2>&1 & OLLAMA_PID=$!
for _ in $(seq 1 60); do curl -fs -m 3 "http://127.0.0.1:$PORT/api/version" >/dev/null && break; sleep 2; done
vm_boot 8 32G || exit 1
"${SSH[@]}" 'mkdir -p ~/official'; "${SCP[@]}" "$REPO/official/fm_local" fm@127.0.0.1:official/
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

# Harbor's kernel probe gives up after 30 s, so a slow Docker Hub pull reads as "no-network unsupported". Cache the exact image first.
"${SSH[@]}" 'for i in 1 2 3 4 5 6; do sudo docker pull -q alpine:3.23.4@sha256:5b10f432ef3da1b8d4c7eb6c487f2f5a8f096bc91145e68878dd4a5019afde11 && break; sleep 20; done'
SER="-n 1"  # one model server, so trials run one at a time; agent time limits would otherwise include queueing

step "Word2Vec without memory, 3 attempts, one at a time"
"${SSH[@]}" "$ENV; $H frontier-memory run-tasks --harness fm_local.hermes_local:LocalHermes $COMMON --tasks data/tasks-fm -k 3 --effort max --job-name compliant2-w2v-nomem --jobs-dir jobs -- $SER -i 'build-word2vec*' 2>&1 | tail -1 | cut -c1-120; sudo chown -R fm:fm jobs/compliant2-w2v-nomem; frontier-memory score jobs/compliant2-w2v-nomem 2>&1 | tail -3 | cut -c1-120"

step "Word2Vec with the generated memory (compliant-gen), 3 attempts, one at a time"
"${SSH[@]}" "$ENV; $H frontier-memory run-tasks --harness fm_local.hermes_local:LocalHermes $COMMON --tasks data/tasks-fm -k 3 --effort max --memory jobs/compliant-gen --job-name compliant2-w2v-mem --jobs-dir jobs -- $SER -i 'build-word2vec*' 2>&1 | tail -1 | cut -c1-120; sudo chown -R fm:fm jobs/compliant2-w2v-mem; frontier-memory score jobs/compliant2-w2v-mem 2>&1 | tail -3 | cut -c1-120; frontier-memory bundle --memory-job jobs/compliant-gen --task-job jobs/compliant2-w2v-mem --out compliant-bundle.tar.gz 2>&1 | tail -22 | cut -c1-170"

step "memory loaded vs absent, per trial"
"${SSH[@]}" "cd ~/official/frontiermemory/jobs; python3 - <<'PY'
import json,glob
for j in ('compliant2-w2v-nomem','compliant2-w2v-mem'):
    for p in sorted(glob.glob(j+'/*__*/result.json')):
        d=json.load(open(p)); a=d.get('agent_result') or {}; e=d.get('exception_info') or {}; m=(a.get('metadata') or {}).get('frontier_memory')
        x=d.get('agent_execution') or {}
        print(j[-5:],p.split('__')[-1][:7],(d.get('verifier_result') or {}).get('rewards'),e.get('exception_type',''),'digest',(m or {}).get('memory_sha256','none')[:10] if isinstance(m,dict) else m,a.get('n_input_tokens'),a.get('n_output_tokens'),x.get('started_at','')[11:19],x.get('finished_at','')[11:19])
PY"

step "APEX judge and key check: agent cut off after about 2 min, then graded. Not counted"
"${SSH[@]}" 'umask 077; cat > ~/.judge-key' < "$HOME/.config/frontiermemory/anthropic-api-key"
"${SSH[@]}" 'nohup bash -c "for i in \$(seq 1 40); do for c in \$(sudo docker ps -q); do sudo docker inspect --format \"{{.Name}}|{{range .Config.Env}}{{println .}}{{end}}\" \$c > /tmp/i.$$; echo \"\$(head -1 /tmp/i.$$ | cut -d\"|\" -f1) real_key_lines=\$(grep -cF \"\$(cat ~/.judge-key)\" /tmp/i.$$) openai=\$(grep -c \"^OPENAI_API_KEY=local-placeholder\" /tmp/i.$$)\"; done; sleep 15; done; rm -f /tmp/i.$$" >> ~/key-audit-gate.log 2>&1 &'
"${SSH[@]}" "$ENV; export JUDGE_ANTHROPIC_KEY=\$(cat ~/.judge-key); sudo env PATH=\$PATH PYTHONPATH=\$PYTHONPATH FM_LOCAL_BASE_URL=\$FM_LOCAL_BASE_URL OPENAI_API_KEY=\$OPENAI_API_KEY JUDGE_ANTHROPIC_KEY=\$JUDGE_ANTHROPIC_KEY frontier-memory run-tasks --harness fm_local.hermes_local:LocalHermes $COMMON --tasks data/tasks-fm -k 1 --effort max --job-name compliant2-apex --jobs-dir jobs -- -n 1 -i 'apex-eurogrid*' --agent-timeout-multiplier 0.01 --ve GRADING_MODEL=anthropic/claude-opus-5-5 --ve 'ANTHROPIC_API_KEY=\${JUDGE_ANTHROPIC_KEY}' 2>&1 | tail -1 | cut -c1-120; sudo chown -R fm:fm jobs/compliant2-apex; d=\$(ls -d jobs/compliant2-apex/*__* | head -1); python3 -c \"import json,sys;d=json.load(open(sys.argv[1]));e=d.get('exception_info') or {};print((d.get('verifier_result') or {}).get('rewards',{}).get('reward'),e.get('exception_type',''))\" \$d/result.json; grep -hE 'GRADING.*END|AuthenticationError' \$d/verifier/grade_log.txt | cut -c1-200 | sort -u | head -3; grep -rlF \"\$(cat ~/.judge-key)\" jobs/compliant2-apex 2>/dev/null | wc -l; sort ~/key-audit-gate.log | cut -d' ' -f2- | sort | uniq -c | head -3; awk '{print \$1,\$2,\$3}' ~/key-audit-gate.log | sed -E 's/__[a-z0-9]+__/__/' | sort | uniq -c | cut -c1-110 | head -8; pkill -f 'key-audit-gate' ; rm -f ~/.judge-key"

step "effort audit, all"; audit; grep -cE "POST +\"/v1/responses\"" "$OLOG/server.log"; grep -E "\| +[0-9]{3} \|" "$OLOG/server.log" | grep -oE "\| +[0-9]{3} \|" | sort | uniq -c; grep -oE "truncated = [0-9]+" "$OLOG/server.log" | sort | uniq -c
"${SSH[@]}" 'df -h / | tail -1'
kill $OLLAMA_PID 2>/dev/null; rm -rf "$OLOG/tmp"
step "GATE_COMPLIANT_DONE"
