#!/bin/bash
# HOLD (D93): the all-sets job (run-all.sbatch) calls this for each remaining set. It keeps the GPUs and runs each
# driver named in official/vm/NEXT, one at a time, until a driver writes official/vm/DRIVER_DONE (touch it to release).
# Drivers always exit 0 and report pass or fail through their own markers, so the job never ends by accident.
cd /home/csgrad/vbork001/frontiermemory-experiment-20261024 || exit 1
while :; do
  [ -f official/vm/DRIVER_DONE ] && { echo "=== ${SET:-?}: driver finished; nothing to do"; exit 0; }
  echo "=== $(date +%m-%d\ %H:%M:%S) ${SET:-?}: HOLD, waiting for official/vm/NEXT"
  while [ ! -f official/vm/NEXT ] && [ ! -f official/vm/DRIVER_DONE ]; do sleep 60; done
  [ -f official/vm/NEXT ] || continue
  N=$(cat official/vm/NEXT); rm -f official/vm/NEXT
  echo "=== $(date +%m-%d\ %H:%M:%S) HOLD released: running $N"
  bash "$N"; echo "=== $(date +%m-%d\ %H:%M:%S) HOLD: $N exited $?"
done
