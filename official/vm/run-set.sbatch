#!/bin/bash
# HOLD (2026-11-04, D93): the running all-sets job calls this file at the start of each set. The setup is being fixed,
# so instead of starting the next set it waits here, keeping the GPUs, until official/vm/NEXT exists, then runs that script.
# The previous run script is official/vm/run-set-v1.sbatch.
cd /home/csgrad/vbork001/frontiermemory-experiment-20261024 || exit 1
[ -f official/vm/DRIVER_DONE ] && { echo "=== ${SET:-?}: driver finished; nothing to do"; exit 0; }
echo "=== $(date +%m-%d\ %H:%M:%S) ${SET:-?}: HOLD, waiting for official/vm/NEXT"
while [ ! -f official/vm/NEXT ]; do sleep 60; done
echo "=== $(date +%m-%d\ %H:%M:%S) HOLD released: running $(cat official/vm/NEXT)"
N=$(cat official/vm/NEXT); rm -f official/vm/NEXT; bash "$N"
