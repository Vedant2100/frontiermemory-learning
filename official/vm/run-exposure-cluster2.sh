#!/bin/bash
# Exposure-arm entry point. It uses the common runner directly; it never edits or derives a script in the clone.
#   E2E=1 bash official/vm/run-exposure-cluster2.sh none|all
#   bash official/vm/run-exposure-cluster2.sh none|all
set -Eeuo pipefail
ARM=${1:?usage: run-exposure-cluster2.sh none|all}
case "$ARM" in none|all) ;; *) echo "exposure arm must be none or all"; exit 2 ;; esac
EXPECTED_MEMORY=${EXPECTED_MEMORY:?set the validated HM1 memory digest}
[[ "$EXPECTED_MEMORY" =~ ^[0-9a-f]{64}$ ]] || { echo BAD_EXPECTED_MEMORY; exit 1; }
REPO=$(realpath "$HOME/frontiermemory-cluster2")
cd "$REPO"
if [ "${E2E:-0}" = 1 ]; then
  exec env SET="exposure-$ARM" TASK_HARNESS="exposure-$ARM" MEMORY_SOURCE=run1 \
    MEMORY_JOB_NAME="${MEMORY_JOB_NAME:-fm-gen-run1}" EXPECTED_MEMORY="$EXPECTED_MEMORY" \
    TASK_JOB_NAME="${TASK_JOB_NAME:-fm-smoke-exposure-$ARM}" EXPOSURE_ARM=1 EXPOSURE_E2E=1 SMOKE=1 \
    bash official/vm/run-set-cluster2.sh
fi
exec env SET="exposure-$ARM" TASK_HARNESS="exposure-$ARM" MEMORY_SOURCE=run1 \
  MEMORY_JOB_NAME="${MEMORY_JOB_NAME:-fm-gen-run1}" EXPECTED_MEMORY="$EXPECTED_MEMORY" \
  TASK_JOB_NAME="${TASK_JOB_NAME:-fm-tasks-exposure-$ARM}" EXPOSURE_ARM=1 SMOKE=0 \
  bash official/vm/run-set-cluster2.sh
