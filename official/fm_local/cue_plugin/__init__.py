"""fm-cue: cue-triggered delivery of saved memory skills (cue arm, results/preregistration-arms.md).

Hermes calls transform_tool_result after every tool call, before the result enters the model's context (model_tools.py,
pinned d923a5eb); the bundled security-guidance plugin appends text the same way. Here, when a call's tool name and
arguments share >= arm_logic.CUE_MIN_SHARED terms with a memory skill's name + description, that skill's full SKILL.md is
appended to the call's result, once per skill per process. A call that names the skill's own folder is the agent opening it
itself: the skill counts as fired, nothing is appended.

Environment (set by fm_local.arm_hermes): FM_CUE_MEMORY = the uploaded memory folder; FM_CUE_LOG = a folder for
fm-cue-metrics.json (counts and skill digests only, rewritten after every call so a killed agent still leaves it).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path

_spec = importlib.util.spec_from_file_location("fm_arm_logic", Path(__file__).with_name("arm_logic.py"))
logic = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(logic)

STATE: dict = {}


def _write_metrics() -> None:
    m = STATE["metrics"]
    path = Path(STATE["log"]) / "fm-cue-metrics.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(m, sort_keys=True))
    os.replace(tmp, path)


def setup(memory: Path, log: Path) -> None:
    found = logic.skills(memory)
    STATE.update(log=str(log), fired=set(),
                 skills={s["rel"]: s for s in found},
                 terms={s["rel"]: logic.cue_terms(f"{s['name']} {s['description']}") for s in found},
                 metrics={"skills": len(found), "hook_calls": 0, "activations": 0, "opened_directly": 0,
                          "inserted_bytes": 0, "fired_sha256": []})
    _write_metrics()


def on_tool_result(tool_name=None, args=None, result=None, **_):
    m = STATE["metrics"]
    m["hook_calls"] += 1
    call_text = f"{tool_name or ''} {json.dumps(args, sort_keys=True, default=str) if args is not None else ''}"
    lowered = call_text.casefold()
    matched = set(logic.cue_match(call_text, STATE["terms"], STATE["fired"]))
    blocks = []
    for rel in sorted(STATE["skills"]):
        if rel in STATE["fired"]:
            continue
        skill = STATE["skills"][rel]
        viewed = str((args or {}).get("name", "") if isinstance(args, dict) else "").casefold()
        direct = (f"skills/{rel}".casefold() in lowered or f"/{skill['leaf']}/".casefold() in lowered
                  or (tool_name == "skill_view" and viewed in {skill["name"].casefold(), skill["leaf"].casefold(), rel.casefold()}))
        if not (direct or rel in matched):
            continue
        STATE["fired"].add(rel)
        m["fired_sha256"].append(hashlib.sha256(skill["text"].encode()).hexdigest()[:16])
        if direct:
            m["opened_directly"] += 1
            continue
        m["activations"] += 1
        m["inserted_bytes"] += len(skill["text"].encode())
        blocks.append(f"[Saved memory skill that matches this step: {skill['name']}]\n{skill['text']}\n[End of saved memory skill]")
    _write_metrics()
    if not blocks:
        return None
    base = result if isinstance(result, str) else json.dumps(result, default=str)
    return base + "\n\n" + "\n\n".join(blocks)


def register(ctx):
    memory, log = os.environ.get("FM_CUE_MEMORY"), os.environ.get("FM_CUE_LOG")
    if not memory or not log:
        raise RuntimeError("fm-cue needs FM_CUE_MEMORY and FM_CUE_LOG")
    setup(Path(memory), Path(log))
    ctx.register_hook("transform_tool_result", on_tool_result)
