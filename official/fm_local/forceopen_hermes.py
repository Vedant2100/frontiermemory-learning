"""Forced-open follow-up: the HM task agent with the note that would have helped placed in the system prompt.

Question this arm answers: in the 17 failed trials where a relevant note was shown by index but never opened, would
reading it have changed the result? Each trial's relevant memory files are put in the prompt through Hermes's
`agent.system_prompt` key, exactly as the all-shown arm does for every file. Hermes's own MEMORY.md block and skills
index stay on as in HM, so the only change from HM is the extra text.

Load through the official hook: --harness fm_local.forceopen_hermes:ForceOpenHermes --ak plan=run1|run4
The task is read from the trial directory name; a task that is not in the plan fails before any model call.
Each trial writes agent/forceopen-report.json: counts and the memory digest only, never memory text.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import yaml

from frontier_memory.agents.hermes import MemoryHermesOptions

from fm_local.hermes_local import LocalHermes

BYTES_PER_TOKEN = 4
MAX_INJECTED_TOKENS = 100_000
SKILL = "skills/agent-evals/eval-task-families/SKILL.md"
REF = "skills/agent-evals/eval-task-families/references/"

# plan -> task-name prefix -> memory files (paths relative to the memory root), or None for every file
PLANS: dict[str, dict[str, list[str] | None]] = {
    "run1": {
        "apex-brightpath-seat-surplus": [SKILL, REF + "paths.md", REF + "family-analysis-mcp.md"],
        "dapt-intrusion-detection": [SKILL, REF + "family-pcap.md"],
        "enterpriseops-teams": [SKILL, REF + "family-office-mcp.md"],
    },
    "run4": {
        "apex-brightpath-seat-surplus": None,
        "dapt-intrusion-detection": None,
        "automationbench-marketing-content-gap": None,
    },
}


class ForceOpenOptions(MemoryHermesOptions):
    plan: Literal["run1", "run4"]


def task_of(trial_logs_dir: Path) -> str:
    """The task id from the trial directory name `<task>__<suffix>` (logs_dir is <trial>/agent)."""
    return trial_logs_dir.parent.name.rsplit("__", 1)[0]


def select_files(plan: str, task: str, memory_dir: Path) -> list[Path]:
    rules = PLANS[plan]
    key = next((k for k in rules if task.startswith(k)), None)
    if key is None:
        raise ValueError(f"task {task!r} is not in plan {plan!r}")
    every = sorted((p for p in memory_dir.rglob("*") if p.is_file()), key=lambda p: p.relative_to(memory_dir).as_posix())
    wanted = rules[key]
    if wanted is None:
        return every
    by_rel = {p.relative_to(memory_dir).as_posix(): p for p in every}
    missing = [w for w in wanted if w not in by_rel]
    if missing:
        raise ValueError(f"plan {plan!r} names files the memory does not have: {missing}")
    return [by_rel[w] for w in wanted]


def injected_text(files: list[Path], memory_dir: Path) -> str:
    parts = ["The following memory files are provided in full."]
    for path in files:
        rel = path.relative_to(memory_dir).as_posix()
        parts.append(f"===== memory file: {rel} =====\n{path.read_text(encoding='utf-8')}\n===== end: {rel} =====")
    return "\n\n".join(parts)


def apply_forceopen(config: dict, text: str) -> dict:
    config = json.loads(json.dumps(config))
    agent = config.setdefault("agent", {})
    if agent.get("system_prompt"):
        raise ValueError("agent.system_prompt is already set; refusing to overwrite it")
    agent["system_prompt"] = text
    return config


def report(plan: str, task: str, files: list[Path], text: str, memory_sha256: str) -> dict:
    n = len(text.encode("utf-8"))
    return {"plan": plan, "task": task, "memory_sha256": memory_sha256, "files_injected": len(files),
            "injected_bytes": n, "injected_tokens_estimate": n // BYTES_PER_TOKEN, "bytes_per_token_estimate": BYTES_PER_TOKEN}


class ForceOpenHermes(LocalHermes):
    options_model = ForceOpenOptions
    options: ForceOpenOptions

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._memory_dir is None:
            raise ValueError("the forced-open arm needs a memory (--memory)")
        self._task = task_of(self.logs_dir)
        files = select_files(self.options.plan, self._task, self._memory_dir)
        self._text = injected_text(files, self._memory_dir)
        self._forceopen_report = report(self.options.plan, self._task, files, self._text, self._memory_report["memory_sha256"])
        if self._forceopen_report["injected_tokens_estimate"] > MAX_INJECTED_TOKENS:
            raise ValueError(f"would inject about {self._forceopen_report['injected_tokens_estimate']} tokens, over {MAX_INJECTED_TOKENS}")

    @staticmethod
    def name() -> str:
        return "frontier-memory-hermes-forceopen"

    def _actor_config(self, model: str) -> str:
        return yaml.safe_dump(apply_forceopen(yaml.safe_load(super()._actor_config(model)), self._text))

    async def run(self, instruction, environment, context):
        path = self.logs_dir / "forceopen-report.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._forceopen_report, indent=1) + "\n")
        return await super().run(instruction, environment, context)

    def populate_context_post_run(self, context) -> None:
        super().populate_context_post_run(context)
        context.metadata = {**(context.metadata or {}), "fm_forceopen": self._forceopen_report}
