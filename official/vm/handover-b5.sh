#!/bin/bash
# B5 hand-over, run inside the job (srun --overlap). Waits for next-study-3.sh to log "exposure-none: SET_CHECKED", then
# stops it at once, before it starts the cue arm (cue is not run, B5), together with anything it started after that line.
# The hold (run-set.sbatch) then runs official/vm/NEXT = next-study-5.sh. If the study stops instead, it does nothing.
DRV=${1:?driver pid}; LOG=/home/csgrad/vbork001/frontiermemory-experiment-20261024/official/logs/set-$SLURM_JOB_ID.log
tree() { local p; for p in $(pgrep -P "$1"); do tree "$p"; echo "$p"; done; }
tail -n0 -F --sleep-interval=0.2 "$LOG" 2>/dev/null | while IFS= read -r l; do
  case "$l" in
    *"exposure-none: SET_CHECKED"*)
      kill -STOP "$DRV"; kids=$(tree "$DRV"); [ -n "$kids" ] && kill -KILL $kids 2>/dev/null; kill -KILL "$DRV"
      echo "=== $(date +%m-%d\ %H:%M:%S) B5 hand-over: next-study-3.sh stopped after none-shown (killed: $DRV ${kids//$'\n'/ })" | tee -a "$LOG"
      pkill -P $$ tail; exit 0 ;;
    *STUDY_STOPPED*) echo "=== $(date +%m-%d\ %H:%M:%S) B5 hand-over: study stopped on its own; nothing done" | tee -a "$LOG"; pkill -P $$ tail; exit 0 ;;
  esac
done
