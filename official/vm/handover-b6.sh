#!/bin/bash
# B6 hand-over, run inside the job (srun --overlap) like handover-b5.sh. Waits in the set log for the generator arm to finish
# (SET_CHECKED of the counted set, or NO_VALID_MEMORY of its generation), then stops next-study-5.sh at once, before it can write
# DRIVER_DONE and release the job, and queues next-study-6.sh (the blend arm) in official/vm/NEXT. If the study stops instead
# (STUDY_STOPPED), it does nothing and the job holds, as it would have.
#   srun --overlap --jobid=<job> -n1 --gres=gpu:0 bash official/vm/handover-b6.sh <pid of next-study-5.sh>
DRV=${1:?pid of next-study-5.sh}
REPO=${REPO:-/home/csgrad/vbork001/frontiermemory-experiment-20261024}
LOG=${LOG:-$REPO/official/logs/set-$SLURM_JOB_ID.log}; NEXT=${NEXT:-$REPO/official/vm/NEXT}
tree() { local p; for p in $(pgrep -P "$1"); do tree "$p"; echo "$p"; done; }
say() { echo "=== $(date +%m-%d\ %H:%M:%S) $*" | tee -a "$LOG"; }
tail -n0 -F --sleep-interval=0.2 "$LOG" 2>/dev/null | while IFS= read -r l; do
  case "$l" in
    *"arm-generator: SET_CHECKED"*|*"arm-generator"*"NO_VALID_MEMORY"*)
      kill -STOP "$DRV"; kids=$(tree "$DRV"); [ -n "$kids" ] && kill -KILL $kids 2>/dev/null; kill -KILL "$DRV"
      echo "$REPO/official/vm/next-study-6.sh" | sed "s#^$REPO/##" > "$NEXT"
      say "B6 hand-over: next-study-5.sh stopped after the generator arm (killed: $DRV ${kids//$'\n'/ }); queued $(cat "$NEXT")"
      pkill -P $$ tail; exit 0 ;;
    *STUDY_STOPPED*) say "B6 hand-over: study stopped on its own; nothing done"; pkill -P $$ tail; exit 0 ;;
  esac
done
