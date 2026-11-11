"""Derive the blend arm's set script (results/preregistration-arms.md, B6) from run-set-v1.sbatch.

A thin layer over derive_arm.py, which is left untouched while other arms run from it: it adds the arm "blend" and its memory
block (rewrite every task's instruction once, in the guest, from run 1's memory), and appends blend_check.py to the arm check.

    python3 official/vm/derive_blend.py blend <run-set-v1.sbatch> <out> [--e2e]
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import derive_arm as D  # noqa: E402

MAP = "~/official/blend/blend-instructions.json"
D.ARMS["blend"] = {"harness": f"fm_local.blend_hermes:BlendHermes --ak arm=blend --ak blend_map=\\$HOME/official/blend/blend-instructions.json",
                   "memory": "blend"}
_memory_block = D.memory_block

BLOCK = ('GENJOB=fm-gen-run1  # HM run 1\'s memory, reused: read in the guest by the rewrite, never printed\n'
         + D.CHECK_MEMORY + ' || { step "$SET: NO_RUN1_MEMORY_FAILED"; exit 1; }\n'
         'step "$SET: rewriting the task descriptions with run 1\'s memory worked in (one sample per task)"\n'
         'G "$ENV; mkdir -p ~/official/blend; python3 ~/official/fm_local/blend_rewrite.py jobs/$GENJOB data/tasks-fm '
         f'{MAP} ~/official/blend/blend-report.json" 2>&1 | tail -25 | cut -c1-200\n'
         'rc=${PIPESTATUS[0]}\n'
         '"${SCP[@]}" "fm@127.0.0.1:official/blend/blend-report.json" "$REPO/results/official/blend-report.json" 2>/dev/null || true\n'
         '[ "$rc" != 3 ] || { step "$SET: NO_VALID_MEMORY: too few valid rewrites; trials not run (B6)"; exit 0; }\n'
         '[ "$rc" = 0 ] || { step "$SET: BLEND_REWRITE_FAILED"; exit 1; }\n'
         'MEM=""\n')


def memory_block(arm: str, spec: dict) -> str:
    return BLOCK if spec["memory"] == "blend" else _memory_block(arm, spec)


D.memory_block = memory_block


def derive(arm: str, src: str, e2e: bool) -> str:
    out = D.derive(arm, src, e2e)
    old = 'arm_check.py jobs/$TASKJOB blend"'
    if out.count(old) != 1:
        raise SystemExit(f"derive_arm.py changed: expected one arm_check call, found {out.count(old)}")
    return out.replace(old, f'arm_check.py jobs/$TASKJOB blend && sudo python3 ~/official/fm_local/blend_check.py jobs/$TASKJOB {MAP}"')


if __name__ == "__main__":
    arm, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
    if arm != "blend":
        raise SystemExit("derive_blend.py derives only the blend arm")
    open(out, "w").write(derive(arm, open(src).read(), "--e2e" in sys.argv))
