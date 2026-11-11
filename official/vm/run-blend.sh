#!/bin/bash
# The blend arm (results/preregistration-arms.md, B6), inside a held allocation (next-study-6.sh). Same shape as run-arm.sh.
#   bash official/vm/run-blend.sh              counted set, 45 trials, job dir fm-tasks-arm-blend
#   E2E=1 bash official/vm/run-blend.sh        uncounted check: the rewrite of all tasks, then one Word2Vec attempt (fm-smoke-arm-blend)
#   DRY_RUN=1 DRY_OUT=<file> bash official/vm/run-blend.sh   write the derived script and stop
set -euo pipefail
REPO=${REPO:-$HOME/frontiermemory-experiment-20261024}
cd "$REPO"
DERIVED=$(mktemp "$REPO/official/vm/.run-blend-XXXX.sbatch")
trap 'rm -f "$DERIVED"' EXIT
FLAG=""; [ "${E2E:-0}" = 1 ] && FLAG=--e2e
python3 official/vm/derive_blend.py blend official/vm/run-set-v1.sbatch "$DERIVED" $FLAG
bash -n "$DERIVED"
[ "${DRY_RUN:-0}" = 1 ] && { cp "$DERIVED" "${DRY_OUT:?}"; exit 0; }
SET=arm-blend SMOKE=${SMOKE:-0} bash "$DERIVED"
