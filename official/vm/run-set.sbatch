#!/bin/bash
# One set under preregistration v2. Safe to resubmit after an interruption: finished trials are kept.
#   sbatch --dependency=singleton --export=ALL,SET=control|run1|run2|run3 official/vm/run-set.sbatch
#   SMOKE=1 runs one Word2Vec attempt under a scratch name and also exercises the rerun path. Never counted.
# Agents get a placeholder key. The judge key reaches only verifiers, through a template, so it is never on a command line or in saved configs.
#SBATCH --job-name=fm-serial
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu02
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=12
#SBATCH --mem=64G
#SBATCH --time=7-00:00:00
#SBATCH --output=official/logs/set-%j.log
: "${SET:?set SET=control|run1|run2|run3}"; SMOKE="${SMOKE:-0}"
PROBE_IMAGE=alpine:3.23.4@sha256:5b10f432ef3da1b8d4c7eb6c487f2f5a8f096bc91145e68878dd4a5019afde11
case "$SET" in control|run1|run2|run3) ;; *) echo "bad SET"; exit 2 ;; esac
REPO=$PWD; source official/vm/lib.sh
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $SET: $*"; }
MODEL=qwen3.8:27b-mtp-q4_K_M; JUDGE=anthropic/claude-opus-5-5; PORT=$(free_port); OLOG=$ROOT/ollama-$SLURM_JOB_ID; mkdir -p "$OLOG/tmp"
apptainer exec --fakeroot --nv --bind /home/csgrad/vbork001/shared-mem-gov-pilot/models:/models --bind "$OLOG:/ollama-logs" \
  --env OLLAMA_MODELS=/models --env OLLAMA_HOST=127.0.0.1:$PORT --env OLLAMA_CONTEXT_LENGTH=262144 --env OLLAMA_KEEP_ALIVE=30m \
  --env OLLAMA_MAX_LOADED_MODELS=1 --env OLLAMA_NUM_PARALLEL=1 --env TMPDIR=/ollama-logs/tmp \
  "$REPO/containers/ollama.sif" ollama serve >>"$OLOG/server.log" 2>&1 & OLLAMA_PID=$!
for _ in $(seq 1 60); do curl -fs -m 3 "http://127.0.0.1:$PORT/api/version" >/dev/null && break; sleep 2; done
curl -fs -m 5 "http://127.0.0.1:$PORT/api/version" >/dev/null || { echo "MODEL_SERVER_FAILED"; exit 1; }
vm_boot 8 40G || exit 1
G() { "${SSH[@]}" "$@"; }
G 'sudo docker ps -aq | xargs -r sudo docker rm -f >/dev/null 2>&1; sudo docker network prune -f >/dev/null 2>&1; for i in 1 2 3 4 5 6; do sudo docker pull -q '"$PROBE_IMAGE"' >/dev/null && break; sleep 20; done; sudo docker image inspect '"$PROBE_IMAGE"' >/dev/null' || { echo "PROBE_IMAGE_MISSING"; exit 1; }
G 'umask 077; cat > ~/.judge-key' < "$HOME/.config/frontiermemory/anthropic-api-key"
"${SCP[@]}" "$REPO/official/fm_local" fm@127.0.0.1:official/
ENV="cd ~/official/frontiermemory; export PATH=\$PWD/.venv/bin:\$PATH PYTHONPATH=\$HOME/official FM_LOCAL_BASE_URL=http://10.0.2.2:$PORT/v1 OPENAI_API_KEY=local-placeholder JUDGE_ANTHROPIC_KEY=\$(cat ~/.judge-key); unset OPENAI_BASE_URL ANTHROPIC_API_KEY"
H="sudo env PATH=\$PATH PYTHONPATH=\$PYTHONPATH FM_LOCAL_BASE_URL=\$FM_LOCAL_BASE_URL OPENAI_API_KEY=\$OPENAI_API_KEY JUDGE_ANTHROPIC_KEY=\$JUDGE_ANTHROPIC_KEY"
COMMON="-m openai/$MODEL -e docker --allow-host 10.0.2.2"
if [ "$SMOKE" = 1 ]; then ATTEMPTS=1; FILTER="-i 'build-word2vec*'"; TASKJOB=fm-smoke-tasks; GENJOB=compliant-gen; else ATTEMPTS=3; FILTER=""; TASKJOB=fm-tasks-$SET; GENJOB=fm-gen-$SET; fi
# One model server, so one trial at a time; agent time limits would otherwise include queueing.
HARBOR_EXTRA="-n 1 $FILTER --ve GRADING_MODEL=$JUDGE --ve 'ANTHROPIC_API_KEY=\${JUDGE_ANTHROPIC_KEY}'"

# Log, every minute, whether any container's config holds the real key. Counts only.
cat > "$OLOG/key-audit.sh" <<'AUDIT'
while true; do
  for c in $(sudo docker ps -q); do
    sudo docker inspect --format '{{.Name}}|{{range .Config.Env}}{{println .}}{{end}}' "$c" > /tmp/ka.$$
    echo "$(date +%H:%M) $(head -1 /tmp/ka.$$ | cut -d'|' -f1 | sed -E 's/__[a-z0-9]{7}__/__/') real_key_lines=$(grep -cF "$(cat ~/.judge-key)" /tmp/ka.$$)"
  done
  rm -f /tmp/ka.$$; sleep 60
done
AUDIT
"${SCP[@]}" "$OLOG/key-audit.sh" fm@127.0.0.1:key-audit.sh
G "nohup bash ~/key-audit.sh >> ~/key-audit-$SET.log 2>&1 < /dev/null & echo \$! > ~/key-audit.pid"

run_tasks() {  # first call starts the job; later calls resume it, keeping finished trials
  local memory="$1"
  if G "[ -f ~/official/frontiermemory/jobs/$TASKJOB/config.json ]"; then
    step "resuming $TASKJOB"
    G "$ENV; $H harbor jobs resume -p jobs/$TASKJOB 2>&1 | tail -1 | cut -c1-140"
  else
    step "starting $TASKJOB"
    G "$ENV; $H frontier-memory run-tasks --harness fm_local.hermes_local:LocalHermes $COMMON --tasks data/tasks-fm -k $ATTEMPTS --effort max $memory --job-name $TASKJOB --jobs-dir jobs -- $HARBOR_EXTRA 2>&1 | tail -1 | cut -c1-140"
  fi
  G "sudo chown -R fm:fm ~/official/frontiermemory/jobs/$TASKJOB"
}

MEM=""
if [ "$SET" != control ] || [ "$SMOKE" = 1 ]; then
  if [ "$SMOKE" != 1 ] && ! G "$ENV; frontier-memory check-memory jobs/$GENJOB >/dev/null 2>&1"; then
    step "fresh generation"
    G "$ENV; [ ! -e jobs/$GENJOB ] || sudo mv jobs/$GENJOB jobs/$GENJOB.failed-\$(date +%s); $H frontier-memory generate-memory --corpus data/corpus/v1.1 --harness fm_local.hermes_local:LocalHermesLearn $COMMON --ak reasoning_effort=max --job-name $GENJOB --jobs-dir jobs 2>&1 | tail -1 | cut -c1-140; sudo chown -R fm:fm jobs/$GENJOB"
  fi
  G "$ENV; frontier-memory check-memory jobs/$GENJOB 2>&1 | tail -8 | cut -c1-120; frontier-memory check-memory jobs/$GENJOB >/dev/null 2>&1" || { step "NO_VALID_MEMORY: reported, trials not run (prereg)"; G 'kill $(cat ~/key-audit.pid); rm -f ~/.judge-key'; exit 0; }
  MEM="--memory jobs/$GENJOB"
fi

run_tasks "$MEM"
for round in 1 2 3; do  # official rule: trials with no reward are rerun and not counted
  n=$(G "cd ~/official/frontiermemory; python3 ~/official/fm_local/set_tools.py set-aside jobs/$TASKJOB")
  step "round $round: $n trial(s) with no reward set aside"
  [ "$n" = 0 ] && break
  run_tasks "$MEM"
done
if [ "$SMOKE" = 1 ]; then
  step "smoke only: exercise the rerun path by setting the finished trial aside as if it had failed"
  G "cd ~/official/frontiermemory; d=\$(ls -d jobs/$TASKJOB/*__* | head -1); mkdir -p jobs/$TASKJOB.smoke-aside; mv \$d jobs/$TASKJOB.smoke-aside/"
  run_tasks "$MEM"
fi

step "score and archive"
G "$ENV; frontier-memory score jobs/$TASKJOB 2>&1 | tail -22 | cut -c1-110; python3 ~/official/fm_local/set_tools.py summary jobs/$TASKJOB > ~/summary-$TASKJOB.jsonl; wc -l < ~/summary-$TASKJOB.jsonl"
[ "$SET" = control ] && [ "$SMOKE" != 1 ] || G "$ENV; frontier-memory bundle --memory-job jobs/$GENJOB --task-job jobs/$TASKJOB --out $TASKJOB-bundle.tar.gz 2>&1 | tail -14 | cut -c1-170"
mkdir -p "$REPO/results/official"; "${SCP[@]}" "fm@127.0.0.1:summary-$TASKJOB.jsonl" "$REPO/results/official/"
G "cut -d' ' -f2- ~/key-audit-$SET.log | sort | uniq -c | sort -rn | head -14 | cut -c1-100; kill \$(cat ~/key-audit.pid); rm -f ~/.judge-key ~/key-audit.pid; ls ~/.judge-key 2>/dev/null | wc -l; df -h / | tail -1"
kill $OLLAMA_PID 2>/dev/null; rm -rf "${OLOG:?}/tmp"
step "SET_DONE"
