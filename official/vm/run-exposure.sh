#!/bin/bash
# One exploratory exposure set: the HM task agent with run 1's memory, start-of-context loading changed (fm_local.exposure_hermes).
#   bash official/vm/run-exposure.sh none|all        counted exploratory set, 45 trials, job dir fm-tasks-exposure-<arm>
#   E2E=1 bash official/vm/run-exposure.sh none|all  uncounted check: one Word2Vec attempt, job dir fm-smoke-exposure-<arm>,
#                                                   plus a check of the first prompt's size against the arm's injected text
# Run inside the held allocation, like run-set-v1.sbatch, after run 3. It never generates memory: without a valid fm-gen-run1 it stops.
# The set script is derived from the current run-set-v1.sbatch with exact replacements, so resume, no-reward reruns, judge, key audit,
# summary and bundle stay identical to the counted sets. Any replacement that no longer matches stops the run.
set -euo pipefail
ARM=${1:?usage: run-exposure.sh none|all}
case "$ARM" in none|all) ;; *) echo "exposure arm must be none or all"; exit 2 ;; esac
REPO=${REPO:-/home/csgrad/vbork001/frontiermemory-experiment-20261024}
cd "$REPO"
DERIVED=$(mktemp "$REPO/official/vm/.run-exposure-$ARM-XXXX.sbatch")
trap 'rm -f "$DERIVED"' EXIT
E2E=${E2E:-0} ARM=$ARM python3 - "$REPO/official/vm/run-set-v1.sbatch" "$DERIVED" <<'PY'
import os, sys
src, out = sys.argv[1], sys.argv[2]
arm, e2e = os.environ["ARM"], os.environ["E2E"] == "1"
s = open(src).read()
pairs = [
    ('case "$SET" in control|run1|run2|run3) ;; *) echo "bad SET"; exit 2 ;; esac',
     'case "$SET" in exposure-none|exposure-all) ;; *) echo "bad SET"; exit 2 ;; esac'),
    ('else ATTEMPTS=3; FILTER=""; TASKJOB=fm-tasks-$SET; GENJOB=fm-gen-$SET; fi',
     "else ATTEMPTS=1; FILTER=\"-i 'build-word2vec*'\"; TASKJOB=fm-smoke-$SET; GENJOB=fm-gen-run1; fi" if e2e else
     'else ATTEMPTS=3; FILTER=""; TASKJOB=fm-tasks-$SET; GENJOB=fm-gen-run1; fi'),
    ('--harness fm_local.hermes_local:LocalHermes $COMMON --tasks',
     f'--harness fm_local.exposure_hermes:ExposureHermes --ak exposure={arm} $COMMON --tasks'),
    ('    step "$SET: fresh generation"',
     '    step "$SET: NO_RUN1_MEMORY_FAILED: exposure sets reuse run 1\'s memory and never generate"; exit 1'),
]
if e2e:
    pairs.append(('\nrun_tasks "$MEM"\nfor round in 1 2 3;',
                  '\nL0=$(wc -l < "$OLOG/server.log" 2>/dev/null || echo 0)\nrun_tasks "$MEM"\nexposure_check "$L0"\nfor round in 1 2 3;'))
    pairs.append(('MODEL=qwen3.8:27b-mtp-q4_K_M; JUDGE=', '''exposure_check() {  # E2E only: did the first prompt carry the arm's memory text? Counts only.
  local first est
  first=$(tail -n +"$(( $1 + 1 ))" "$OLOG/server.log" | grep -oE 'task.n_tokens = [0-9]+' | head -1 | grep -oE '[0-9]+$' || true)
  est=$(G "cd ~/official/frontiermemory; sudo find jobs/$TASKJOB -name exposure-report.json | head -1 | xargs -r sudo python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))[\\"injected_tokens_estimate\\"])'")
  echo "EXPOSURE_CHECK arm=${SET#exposure-} first_prompt_tokens=${first:-none} injected_tokens_estimate=${est:-none}"
  if [ "$SET" = exposure-all ] && { [ -z "$first" ] || [ -z "$est" ] || [ "$first" -lt "$est" ]; }; then echo "EXPOSURE_CHECK_FAILED"; exit 1; fi
}
MODEL=qwen3.8:27b-mtp-q4_K_M; JUDGE='''))
for a, b in pairs:
    n = s.count(a)
    if n != 1:
        sys.exit(f"run-set-v1.sbatch changed: expected one match, found {n}: {a[:70]!r}")
    s = s.replace(a, b)
open(out, "w").write(s)
PY
bash -n "$DERIVED"
[ "${DRY_RUN:-0}" = 1 ] && { cp "$DERIVED" "${DRY_OUT:?}"; exit 0; }
SET=exposure-$ARM SMOKE=0 bash "$DERIVED"
