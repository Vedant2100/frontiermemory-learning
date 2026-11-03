#!/bin/bash
# One counted set under preregistration v2. Submit with: sbatch --dependency=singleton --export=ALL,SET=control|run1|run2|run3 official/vm/run-set.sbatch
# Agents get a placeholder key. The judge key reaches only verifiers, through a template, so it is never on a command line or in saved configs.
#SBATCH --job-name=fm-serial
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu02
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=12
#SBATCH --mem=64G
#SBATCH --time=7-00:00:00
#SBATCH --output=official/logs/set-%x-%j.log
: "${SET:?set SET=control|run1|run2|run3}"
REPO=$PWD; source official/vm/lib.sh
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $SET: $*"; }
MODEL=qwen3.8:27b-mtp-q4_K_M; JUDGE=anthropic/claude-opus-5-5; PORT=$(free_port); OLOG=$ROOT/ollama-$SLURM_JOB_ID; mkdir -p "$OLOG/tmp"
apptainer exec --fakeroot --nv --bind /home/csgrad/vbork001/shared-mem-gov-pilot/models:/models --bind "$OLOG:/ollama-logs" \
  --env OLLAMA_MODELS=/models --env OLLAMA_HOST=127.0.0.1:$PORT --env OLLAMA_CONTEXT_LENGTH=262144 --env OLLAMA_KEEP_ALIVE=30m \
  --env OLLAMA_MAX_LOADED_MODELS=1 --env OLLAMA_NUM_PARALLEL=1 --env TMPDIR=/ollama-logs/tmp \
  "$REPO/containers/ollama.sif" ollama serve >>"$OLOG/server.log" 2>&1 & OLLAMA_PID=$!
for _ in $(seq 1 60); do curl -fs -m 3 "http://127.0.0.1:$PORT/api/version" >/dev/null && break; sleep 2; done
vm_boot 8 40G || exit 1
"${SSH[@]}" 'for i in 1 2 3 4 5 6; do sudo docker pull -q alpine:3.23.4@sha256:5b10f432ef3da1b8d4c7eb6c487f2f5a8f096bc91145e68878dd4a5019afde11 && break; sleep 20; done'  # Harbor's kernel probe image: an uncached slow pull reads as "no-network unsupported"
"${SSH[@]}" 'umask 077; cat > ~/.judge-key' < "$HOME/.config/frontiermemory/anthropic-api-key"
"${SCP[@]}" "$REPO/official/fm_local" fm@127.0.0.1:official/
ENV="cd ~/official/frontiermemory; export PATH=\$PWD/.venv/bin:\$PATH PYTHONPATH=\$HOME/official FM_LOCAL_BASE_URL=http://10.0.2.2:$PORT/v1 OPENAI_API_KEY=local-placeholder JUDGE_ANTHROPIC_KEY=\$(cat ~/.judge-key); unset OPENAI_BASE_URL"
H="sudo env PATH=\$PATH PYTHONPATH=\$PYTHONPATH FM_LOCAL_BASE_URL=\$FM_LOCAL_BASE_URL OPENAI_API_KEY=\$OPENAI_API_KEY JUDGE_ANTHROPIC_KEY=\$JUDGE_ANTHROPIC_KEY"
COMMON="-m openai/$MODEL -e docker --allow-host 10.0.2.2"
TASK_ARGS="--tasks data/tasks-fm -k 3 --effort max --jobs-dir jobs"
# One model server, so one trial at a time; agent time limits would otherwise include queueing.
JUDGE_ARGS="-n 1 --ve GRADING_MODEL=$JUDGE --ve 'ANTHROPIC_API_KEY=\${JUDGE_ANTHROPIC_KEY}'"

# Log, every minute, whether any agent container holds the real key. Counts only.
"${SSH[@]}" 'nohup bash -c "while true; do for c in \$(sudo docker ps -q); do n=\$(sudo docker inspect --format \"{{.Name}} {{range .Config.Env}}{{println .}}{{end}}\" \$c); h=\$(printf %s \"\$n\" | grep -cF \"\$(cat ~/.judge-key)\"); echo \"\$(date +%H:%M) \$(printf %s \"\$n\" | head -1 | cut -d\" \" -f1) key_lines=\$h\"; done; sleep 60; done" >> ~/key-audit-'"$SET"'.log 2>&1 &'

if [ "$SET" = control ]; then
  step "no-memory control, 45 trials"
  "${SSH[@]}" "$ENV; $H frontier-memory run-tasks --harness fm_local.hermes_local:LocalHermes $COMMON $TASK_ARGS --job-name fm-tasks-control -- $JUDGE_ARGS 2>&1 | tail -1 | cut -c1-140"
  TASKJOB=fm-tasks-control
else
  step "fresh generation"
  "${SSH[@]}" "$ENV; $H frontier-memory generate-memory --corpus data/corpus/v1.1 --harness fm_local.hermes_local:LocalHermesLearn $COMMON --ak reasoning_effort=max --job-name fm-gen-$SET --jobs-dir jobs 2>&1 | tail -1 | cut -c1-140; sudo chown -R fm:fm jobs/fm-gen-$SET; frontier-memory check-memory jobs/fm-gen-$SET 2>&1 | tail -8 | cut -c1-120" 
  step "45 trials with that memory"
  "${SSH[@]}" "$ENV; $H frontier-memory run-tasks --harness fm_local.hermes_local:LocalHermes $COMMON $TASK_ARGS --memory jobs/fm-gen-$SET --job-name fm-tasks-$SET -- $JUDGE_ARGS 2>&1 | tail -1 | cut -c1-140"
  TASKJOB=fm-tasks-$SET
fi
step "score and archive"
"${SSH[@]}" "$ENV; sudo chown -R fm:fm jobs/$TASKJOB; frontier-memory score jobs/$TASKJOB 2>&1 | tail -22 | cut -c1-110; [ $SET = control ] || frontier-memory bundle --memory-job jobs/fm-gen-$SET --task-job jobs/$TASKJOB --out $SET-bundle.tar.gz 2>&1 | tail -14 | cut -c1-170; awk '{print \$2,\$3}' ~/key-audit-$SET.log | sort | uniq -c | sort -rn | head -14; df -h / | tail -1; sudo docker system df | cut -c1-70; pkill -f 'key-audit' ; rm -f ~/.judge-key"
kill $OLLAMA_PID 2>/dev/null; rm -rf "$OLOG/tmp"
step "SET_DONE"
