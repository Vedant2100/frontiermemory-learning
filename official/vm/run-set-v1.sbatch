#!/bin/bash
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
#SBATCH --output=official/logs/set-%j.log
: "${SET:?set SET=control|run1|run2|run3}"; SMOKE="${SMOKE:-0}"
case "$SET" in control|run1|run2|run3) ;; *) echo "bad SET"; exit 2 ;; esac
REPO=$PWD; source official/vm/lib.sh
MODEL=qwen3.8:27b-mtp-q4_K_M; JUDGE=anthropic/claude-opus-5-5
model_up "$REPO" || exit 1
vm_boot 8 40G || exit 1
G 'grep -q "\"enabled\":false" /etc/docker/daemon.json' || { echo "BUILD_CACHE_GC_NOT_OFF"; exit 1; }
G 'sudo docker ps -aq | xargs -r sudo docker rm -f >/dev/null 2>&1; sudo docker network prune -f >/dev/null 2>&1; for i in 1 2 3 4 5 6; do sudo docker pull -q '"$PROBE_IMAGE"' >/dev/null && break; sleep 20; done; sudo docker image inspect '"$PROBE_IMAGE"' >/dev/null' || { echo "PROBE_IMAGE_MISSING"; exit 1; }
G 'umask 077; cat > ~/.judge-key' < "$HOME/.config/frontiermemory/anthropic-api-key"
"${SCP[@]}" "$REPO/official/fm_local" fm@127.0.0.1:official/
ENV="cd ~/official/frontiermemory; export PATH=\$PWD/.venv/bin:\$PATH PYTHONPATH=\$HOME/official FM_LOCAL_BASE_URL=http://10.0.2.2:$RELAY_PORT/v1 OPENAI_API_KEY=local-placeholder; unset OPENAI_BASE_URL ANTHROPIC_API_KEY"
H="sudo env PATH=\$PATH PYTHONPATH=\$PYTHONPATH FM_LOCAL_BASE_URL=\$FM_LOCAL_BASE_URL OPENAI_API_KEY=\$OPENAI_API_KEY bash \$HOME/official/fm_local/with_judge_key.sh"
COMMON="-m openai/$MODEL -e docker --allow-host 10.0.2.2"
if [ "$SMOKE" = apex ]; then ATTEMPTS=1; FILTER="-i 'apex-eurogrid*' --agent-timeout-multiplier 0.01"; TASKJOB=fm-smoke-apex
elif [ "$SMOKE" = gate ]; then ATTEMPTS=1; FILTER="${GATE_FILTER:?}"; TASKJOB=${GATE_TASKJOB:?}; GENJOB=${GATE_GENJOB:?}  # restart gate (A2), never counted
elif [ "$SMOKE" = 1 ]; then ATTEMPTS=1; FILTER="-i 'build-word2vec*'"; TASKJOB=fm-smoke-tasks; GENJOB=compliant-gen; else ATTEMPTS=3; FILTER=""; TASKJOB=fm-tasks-$SET; GENJOB=fm-gen-$SET; fi
# One model server, so one trial at a time; agent time limits would otherwise include queueing.
HARBOR_EXTRA="-n 1 $FILTER --ve GRADING_MODEL=$JUDGE --ve 'ANTHROPIC_API_KEY=\${JUDGE_ANTHROPIC_KEY}'"

G "nohup bash ~/official/fm_local/key_audit.sh >> ~/key-audit-$SET.log 2>&1 < /dev/null &"
G 'sudo docker system df | grep -E "Build Cache" | cut -c1-70'

run_tasks() {  # first call starts the job; later calls resume it, keeping finished trials
  local memory="$1"
  if G "[ -f ~/official/frontiermemory/jobs/$TASKJOB/config.json ]"; then
    step "$SET: resuming $TASKJOB"
    G "$ENV; $H harbor jobs resume -p jobs/$TASKJOB 2>&1 | tail -1 | cut -c1-140"
  else
    step "$SET: starting $TASKJOB"
    G "$ENV; $H frontier-memory run-tasks --harness fm_local.hermes_local:LocalHermes $COMMON --tasks data/tasks-fm -k $ATTEMPTS --effort max $memory --job-name $TASKJOB --jobs-dir jobs -- $HARBOR_EXTRA 2>&1 | tail -1 | cut -c1-140"
  fi
  G "sudo chown -R fm:fm ~/official/frontiermemory/jobs/$TASKJOB"
}

MEM=""
if [ "$SET" != control ] || [ "$SMOKE" = 1 ]; then
  if [ "$SMOKE" != 1 ] && ! G "$ENV; frontier-memory check-memory jobs/$GENJOB >/dev/null 2>&1"; then
    step "$SET: fresh generation"
    G "$ENV; [ ! -e jobs/$GENJOB ] || sudo mv jobs/$GENJOB jobs/$GENJOB.failed-\$(date +%s); $H frontier-memory generate-memory --corpus data/corpus/v1.1 --harness fm_local.hermes_local:LocalHermesLearn $COMMON --ak reasoning_effort=max --job-name $GENJOB --jobs-dir jobs 2>&1 | tail -1 | cut -c1-140; sudo chown -R fm:fm jobs/$GENJOB"
  fi
  G "$ENV; frontier-memory check-memory jobs/$GENJOB 2>&1 | tail -8 | cut -c1-120; frontier-memory check-memory jobs/$GENJOB >/dev/null 2>&1" || { step "$SET: NO_VALID_MEMORY: reported, trials not run (prereg)"; exit 0; }
  MEM="--memory jobs/$GENJOB"
fi

run_tasks "$MEM"
for round in 1 2 3; do  # official rule: trials with no reward are rerun and not counted
  n=$(G "$ENV; python3 ~/official/fm_local/set_tools.py set-aside jobs/$TASKJOB")
  step "$SET: round $round: $n trial(s) with no reward set aside"
  [ "$n" = 0 ] && break
  run_tasks "$MEM"
done
if [ "$SMOKE" = 1 ]; then
  step "$SET: smoke only: exercise the rerun path by setting the finished trial aside as if it had failed"
  G "cd ~/official/frontiermemory; d=\$(ls -d jobs/$TASKJOB/*__* | head -1); mkdir -p jobs/$TASKJOB.smoke-aside; mv \$d jobs/$TASKJOB.smoke-aside/"
  run_tasks "$MEM"
fi

step "$SET: score and archive"
G "$ENV; frontier-memory score jobs/$TASKJOB 2>&1 | tail -22 | cut -c1-110; python3 ~/official/fm_local/set_tools.py summary jobs/$TASKJOB > ~/summary-$TASKJOB.jsonl; wc -l < ~/summary-$TASKJOB.jsonl; python3 -c \"
import collections,json,sys
print('judge status', dict(collections.Counter(json.loads(l).get('judge_status') for l in open(sys.argv[1]))))\" ~/summary-$TASKJOB.jsonl"
[ "$SET" = control ] && [ "$SMOKE" != 1 ] || G "$ENV; frontier-memory bundle --memory-job jobs/$GENJOB --task-job jobs/$TASKJOB --out $TASKJOB-bundle.tar.gz 2>&1 | tail -14 | cut -c1-170"
mkdir -p "$REPO/results/official"; "${SCP[@]}" "fm@127.0.0.1:summary-$TASKJOB.jsonl" "$REPO/results/official/"
G "cut -d' ' -f2- ~/key-audit-$SET.log | sort | uniq -c | sort -rn | head -14 | cut -c1-150; echo \"saved files holding the key: \$(sudo grep -rlF \"\$(cat ~/.judge-key)\" ~/official/frontiermemory/jobs/$TASKJOB 2>/dev/null | wc -l)\"; sudo docker system df | grep -E 'Build Cache' | cut -c1-70; df -h / | tail -1"
"${SCP[@]}" "$REPO/official/vm/audit-set.py" fm@127.0.0.1:audit-set.py; G "cd ~/official/frontiermemory; sudo python3 ~/audit-set.py jobs/$TASKJOB" > "$REPO/results/official/audit-$TASKJOB.txt" 2>&1; tail -3 "$REPO/results/official/audit-$TASKJOB.txt"
vm_stop; trap - EXIT; kill $OLLAMA_PID 2>/dev/null; pkill -u "$USER" -x ollama; rm -rf "${OLOG:?}/tmp"
step "$SET: SET_DONE"
