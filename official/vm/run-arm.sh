#!/bin/bash
# One exploratory arm (results/preregistration-arms.md), inside a held allocation (run-arms.sbatch -> next-study-3.sh).
#   bash official/vm/run-arm.sh <arm>              counted set, 45 trials, job dir fm-tasks-arm-<arm>
#   E2E=1 bash official/vm/run-arm.sh <arm>        uncounted check: one Word2Vec attempt, job dir fm-smoke-arm-<arm>
#   SMOKE=gate GATE_TASKJOB=.. GATE_FILTER=.. GATE_GENJOB=.. bash official/vm/run-arm.sh <c0|cm|k0|km>   harness gate part
#   DRY_RUN=1 DRY_OUT=<file> bash official/vm/run-arm.sh <arm>   write the derived script and stop
# The set script is derived from run-set-v1.sbatch by exact replacements (derive_arm.py); arms: derive_arm.py --list.
set -euo pipefail
ARM=${1:?usage: run-arm.sh <arm>}
REPO=${REPO:-$HOME/frontiermemory-experiment-20261024}
cd "$REPO"
DERIVED=$(mktemp "$REPO/official/vm/.run-arm-$ARM-XXXX.sbatch")
trap 'rm -f "$DERIVED"' EXIT
FLAG=""; [ "${E2E:-0}" = 1 ] && FLAG=--e2e
python3 official/vm/derive_arm.py "$ARM" official/vm/run-set-v1.sbatch "$DERIVED" $FLAG
bash -n "$DERIVED"
[ "${DRY_RUN:-0}" = 1 ] && { cp "$DERIVED" "${DRY_OUT:?}"; exit 0; }
SET=arm-$ARM SMOKE=${SMOKE:-0} bash "$DERIVED"
