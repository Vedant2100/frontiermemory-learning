#!/bin/bash
# Forced-open follow-up set, derived from run-set-v1.sbatch with exact replacements (any that stops matching aborts).
#   bash official/vm/run-forceopen.sh run1|run4 [submit]     with no 'submit', only writes the derived script and checks it
# Counted? No: exploratory, reported separately. Memory is the existing run 1 or run 4 memory; nothing is generated.
# Safety: the guest boots from a copy-on-write overlay of the study disk, so the study disk is only read.
# Output: jobs/fm-tasks-forceopen-<plan> in the overlay, copied to $HOME/fm-followup-forceopen-<plan>.tgz, summary and audit in results/official.
set -euo pipefail
PLAN=${1:?usage: run-forceopen.sh run1|run4 [submit]}
case "$PLAN" in run1|run4) ;; *) echo "plan must be run1 or run4"; exit 2 ;; esac
REPO=${REPO:-$PWD}; cd "$REPO"
OUT=official/vm/.run-forceopen-$PLAN.sbatch
PLAN=$PLAN python3 - official/vm/run-set-v1.sbatch "$OUT" <<'PY'
import os, sys
src, out = sys.argv[1], sys.argv[2]
plan = os.environ["PLAN"]
tasks = {"run1": ["apex-brightpath-seat-surplus*", "dapt-*", "enterpriseops-teams*"],
         "run4": ["apex-brightpath-seat-surplus*", "dapt-*", "automationbench-marketing-content-gap*"]}[plan]
flt = " ".join(f"-i '{t}'" for t in tasks)
s = open(src).read()
pairs = [
    ('case "$SET" in control|run1|run2|run3) ;; *) echo "bad SET"; exit 2 ;; esac',
     'case "$SET" in forceopen-run1|forceopen-run4) ;; *) echo "bad SET"; exit 2 ;; esac'),
    ('REPO=$PWD; source official/vm/lib.sh\n',
     'REPO=$PWD; source official/vm/lib.sh\n'
     'ORIG=/scratch/$USER/fm-vm; FUP=/scratch/$USER/fm-vm-followup; mkdir -p "$FUP"\n'
     '[ -f "$FUP/disk.qcow2" ] || "$T/usr/bin/qemu-img" create -q -f qcow2 -F qcow2 -b "$ORIG/disk.qcow2" "$FUP/disk.qcow2" || exit 1\n'
     'for f in seed id id.pub; do [ -e "$FUP/$f" ] || ln -s "$ORIG/$f" "$FUP/$f"; done; ROOT=$FUP\n'),
    ('else ATTEMPTS=3; FILTER=""; TASKJOB=fm-tasks-$SET; GENJOB=fm-gen-$SET; fi',
     f'else ATTEMPTS=3; FILTER="{flt}"; TASKJOB=fm-tasks-$SET; GENJOB=fm-gen-${{SET#forceopen-}}; fi'),
    ('--harness fm_local.hermes_local:LocalHermes $COMMON --tasks',
     '--harness fm_local.forceopen_hermes:ForceOpenHermes --ak plan=${SET#forceopen-} $COMMON --tasks'),
    ('    step "$SET: fresh generation"',
     '    step "$SET: NO_MEMORY_FAILED: the forced-open sets reuse an existing memory and never generate"; exit 1'),
    ('vm_stop; trap - EXIT; kill $OLLAMA_PID',
     'G "cd ~/official/frontiermemory; sudo tar -czf - jobs/$TASKJOB" > "$HOME/fm-followup-$SET.tgz"; ls -l "$HOME/fm-followup-$SET.tgz"\n'
     'vm_stop; trap - EXIT; kill $OLLAMA_PID'),
]
for a, b in pairs:
    n = s.count(a)
    if n != 1:
        sys.exit(f"run-set-v1.sbatch changed: expected one match, found {n}: {a[:70]!r}")
    s = s.replace(a, b)
open(out, "w").write(s)
PY
bash -n "$OUT"
echo "derived $OUT"
[ "${2:-}" = submit ] || exit 0
sbatch --dependency=singleton --export=ALL,SET=forceopen-$PLAN,SMOKE=0 "$OUT"
