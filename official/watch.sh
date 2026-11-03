#!/bin/bash
# Event stream for the study; each stdout line is one event. Read-only: never changes a job. State in $S survives re-arming.
# Events: job state changes, new step markers and failure lines in job logs, finished trials, and no model traffic for 45 min.
cd /home/csgrad/vbork001/frontiermemory-experiment-20261024 || exit 1
S=$HOME/.cache/fm-watch; mkdir -p "$S"
PAT='^=== |ORACLE_|^BAD |_FAILED|_MISSING|NO_VALID_MEMORY|SET_DONE|PROVISION_DONE|FREEZE_DONE|BUILD_CACHE_GC_NOT_OFF|Traceback|error:|CANCELLED|DUE TO|no space left|No space left|SSH never|Killed|oom'
probe() {  # runs on the job's node, inside its allocation; counts only
  cat <<'EOF'
Q=$(pgrep -u $USER -f qemu-kvm | head -1); [ -n "$Q" ] || { echo "vm=down"; exit 0; }
P=$(tr '\0' ' ' </proc/$Q/cmdline | grep -oE "hostfwd=tcp:127.0.0.1:[0-9]+" | grep -oE "[0-9]+$")
L=$(ls -t /scratch/$USER/fm-vm/ollama-*/server.log 2>/dev/null | head -1)
A=-1; [ -n "$L" ] && A=$(( $(date +%s) - $(stat -c %Y "$L") ))
ssh -i /scratch/$USER/fm-vm/id -p "$P" -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR fm@127.0.0.1 'cd ~/official/frontiermemory/jobs 2>/dev/null || exit 0
for j in fm-tasks-* fm-smoke-tasks; do [ -f "$j/config.json" ] || continue; d=0; n=0; for r in "$j"/*__*/result.json; do [ -f "$r" ] && d=$((d+1)); done; for t in "$j"/*__*; do [ -d "$t" ] && n=$((n+1)); done; printf "%s done=%s started=%s\n" "$j" "$d" "$n"; done
printf "disk=%s\n" "$(df --output=pcent / | tail -1 | tr -d " %")"' 2>/dev/null
echo "model_log_age=$A"
EOF
}
tick=0
while true; do
  now=$(squeue -u "$USER" -h -t PD,R,CG -o "%i %T %j %r" 2>/dev/null | grep -v fm-held | sort)
  if [ "$now" != "$(cat "$S/q" 2>/dev/null)" ]; then
    comm -13 <(sort "$S/q" 2>/dev/null) <(echo "$now") | sed '/^$/d; s/^/JOB /'
    for j in $(comm -23 <(cut -d' ' -f1 "$S/q" 2>/dev/null | sort -u) <(echo "$now" | cut -d' ' -f1 | sort -u)); do
      [ -n "$j" ] && echo "JOB_ENDED $j $(sacct -j "$j" -X -n -o State%14,Elapsed,ExitCode 2>/dev/null | tr -s ' ')"
    done
    echo "$now" > "$S/q"
  fi
  for f in official/logs/*.log; do
    [ "$(stat -c %Y "$f")" -gt "$(date -d '3 days ago' +%s)" ] || continue
    k=$S/$(basename "$f").n; old=$(cat "$k" 2>/dev/null); cur=$(wc -l < "$f")
    [ -z "$old" ] && [ "$tick" = 0 ] && [ "$(stat -c %Y "$f")" -lt "$(date -d '5 minutes ago' +%s)" ] && { echo "$cur" > "$k"; continue; }
    if [ "${old:-0}" != "$cur" ]; then
      sed -n "$(( ${old:-0} + 1 )),${cur}p" "$f" | grep -E "$PAT" | sed -E 's/sk-[A-Za-z0-9_-]{8,}/sk-REDACTED/g' | cut -c1-170 | sed "s|^|$(basename "$f" .log): |"
      echo "$cur" > "$k"
    fi
  done
  if [ $((tick % 15)) = 0 ]; then
    J=$(squeue -u "$USER" -h -t R -n fm-serial -o %i | head -1)
    if [ -n "$J" ]; then
      R=$(probe | timeout 60 srun --jobid="$J" --overlap -n1 -c1 --mem=100M bash /dev/stdin 2>/dev/null)
      while read -r name d n; do
        case "$name" in fm-tasks-*|fm-smoke-tasks) k=$S/$J.$name; [ "$d" != "$(cat "$k" 2>/dev/null)" ] && { echo "TRIALS $name finished=${d#done=} ${n}"; echo "$d" > "$k"; } ;; esac
      done <<< "$(echo "$R" | grep -E '^fm-')"
      a=$(echo "$R" | sed -n 's/^model_log_age=//p'); [ "${a:-0}" -gt 2700 ] && echo "STALL no model traffic for $((a/60)) min on job $J"
      u=$(echo "$R" | sed -n 's/^disk=//p'); [ "${u:-0}" -ge 80 ] && echo "DISK guest at ${u}%"
      echo "$R" | grep -q '^vm=down' && echo "VM_DOWN job $J"
    fi
  fi
  tick=$((tick+1)); sleep 60
done
