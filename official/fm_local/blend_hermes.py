"""Blend arm (results/preregistration-arms.md, B6): the HM task agent (LocalHermes) with no memory at all and a rewritten task
description, in which run 1's memory was worked into the task text by blend_rewrite.py. Nothing else differs from the control.

Load through the official hook:
    --harness fm_local.blend_hermes:BlendHermes --ak arm=blend --ak blend_map=<blend-instructions.json>

A task whose rewrite failed the contract (or that is missing from the map) runs its original instruction, and its report says so;
the analysis leaves those tasks out. Each trial writes agent/arm-report.json: hashes and counts only, never task or memory text.
The instruction the agent receives must hash to the original recorded at rewrite time, so a changed task cannot slip through.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from frontier_memory.agents.hermes import MemoryHermesOptions

from fm_local import blend_logic
from fm_local.hermes_local import LocalHermes


class BlendHermesOptions(MemoryHermesOptions):
    arm: Literal["blend"]
    blend_map: str  # JSON written by blend_rewrite.py


class BlendHermes(LocalHermes):
    options_model = BlendHermesOptions
    options: BlendHermesOptions

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._memory_dir is not None:
            raise ValueError("arm blend carries its memory in the task description; run it without --memory")
        path = Path(self.options.blend_map)
        if not path.is_file():
            raise ValueError("arm blend needs blend_map (run blend_rewrite.py first)")
        self._map = json.loads(path.read_text())
        self._report = {"arm": "blend"}

    @staticmethod
    def name() -> str:
        return "frontier-memory-hermes-blend"

    async def run(self, instruction, environment, context):
        task = environment.environment_name
        entry = self._map.get(task)
        report = self._report
        report.update(task=task, orig_sha256=blend_logic.sha(instruction), orig_chars=len(instruction.strip()))
        if entry is None:
            raise ValueError(f"task {task!r} not in blend_map")
        if entry["orig_sha"] != report["orig_sha256"]:
            raise ValueError("the task instruction is not the one that was rewritten")
        text = entry["blend"] if entry.get("ok") and entry.get("blend") else None
        report.update(blended=text is not None, blend_sha256=blend_logic.sha(text) if text else report["orig_sha256"],
                      blend_chars=len(text.strip()) if text else report["orig_chars"],
                      added_sentences=entry.get("added_sentences", 0), rolls=entry.get("rolls"))
        path = self.logs_dir / "arm-report.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=1) + "\n")
        return await super().run(text if text is not None else instruction, environment, context)

    def populate_context_post_run(self, context) -> None:
        super().populate_context_post_run(context)
        context.metadata = {**(context.metadata or {}), "fm_arm": self._report}
