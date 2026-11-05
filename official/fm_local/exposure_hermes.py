"""Exploratory exposure arms: the HM task agent (LocalHermes) with only the start-of-context memory changed.

Load through the official hook: --harness fm_local.exposure_hermes:ExposureHermes --ak exposure=none|all
`exposure` has no default, so leaving it out fails before any trial runs.

What pinned Hermes d923a5eb shows at start, with memory on (HM):
  - MEMORY.md, read from $HERMES_HOME/memories, as a frozen system-prompt block (tools/memory_tool_store.py,
    agent/system_prompt.py `_memory_parts`);
  - an <available_skills> index built from $HERMES_HOME/skills (agent/prompt_builder.py).
Every other memory file is only reachable with tools.

  exposure=none  memory block off, and the memory's skills are not placed in $HERMES_HOME/skills, so neither is shown.
                 The whole memory folder, skills included, is still uploaded to $HERMES_HOME/memories for the agent
                 to open. Hermes's own bundled skills are untouched, as in every arm.
  exposure=all   HM's start-of-context, plus the full text of every memory file, in sorted path order, through Hermes's
                 supported `agent.system_prompt` config key, which it adds to the system prompt on every call
                 (hermes_cli/personality.py, agent/codex_runtime.py). The official adapter leaves that key unset.

Each trial writes agent/exposure-report.json: counts and the memory digest only, never memory text or file names.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import yaml

from frontier_memory.agents.hermes import ACTOR_HOME, MemoryHermesOptions

from fm_local.hermes_local import LocalHermes

BYTES_PER_TOKEN = 4  # the estimate the harness survey uses (results/harness-exposure-survey.md)
MAX_INJECTED_TOKENS = 100_000  # "all" must leave most of the 262,144-token context for the task
SKILLS_TARGET = f"{ACTOR_HOME}/skills"
MEMORIES_TARGET = f"{ACTOR_HOME}/memories"
OBSERVER_ID = "fm-delivery-c2"
OBSERVER_TARGET = f"{ACTOR_HOME}/plugins/{OBSERVER_ID}"


class ExposureHermesOptions(MemoryHermesOptions):
    exposure: Literal["none", "all"]


def memory_files(memory_dir: Path) -> list[Path]:
    """Every file in the memory, in a fixed order (sorted relative POSIX path)."""
    return sorted((p for p in memory_dir.rglob("*") if p.is_file()), key=lambda p: p.relative_to(memory_dir).as_posix())


def injected_text(memory_dir: Path) -> str:
    """The `all` arm's extra system-prompt text: each memory file in full, under its relative path."""
    parts = ["The following memory files are provided in full."]
    for path in memory_files(memory_dir):
        rel = path.relative_to(memory_dir).as_posix()
        parts.append(f"===== memory file: {rel} =====\n{path.read_text(encoding='utf-8')}\n===== end: {rel} =====")
    return "\n\n".join(parts)


def apply_exposure(config: dict, exposure: str, memory_dir: Path) -> dict:
    """Return HM's Hermes config changed for one exposure arm. Only memory loading changes."""
    config = json.loads(json.dumps(config))  # deep copy; the config is plain YAML data
    if exposure == "none":
        config["memory"]["memory_enabled"] = False
        config["memory"]["user_profile_enabled"] = False
    elif exposure == "all":
        agent = config.setdefault("agent", {})
        if agent.get("system_prompt"):
            raise ValueError("agent.system_prompt is already set; refusing to overwrite it")
        agent["system_prompt"] = injected_text(memory_dir)
    else:
        raise ValueError(f"unknown exposure {exposure!r}")
    return config


def skip_upload(exposure: str, target: str) -> bool:
    """`none` keeps the memory's skills out of the directory Hermes indexes; everything else uploads as in HM."""
    return exposure == "none" and target.rstrip("/") == SKILLS_TARGET


def report(exposure: str, memory_dir: Path, memory_sha256: str) -> dict:
    files = memory_files(memory_dir)
    total = sum(p.stat().st_size for p in files)
    memory_md = memory_dir / "MEMORY.md"
    out = {"exposure": exposure, "memory_sha256": memory_sha256, "memory_files": len(files), "memory_bytes": total,
           "skill_files": sum(p.name == "SKILL.md" for p in files), "bytes_per_token_estimate": BYTES_PER_TOKEN}
    if exposure == "none":
        out.update(memory_block_shown=False, skills_index_shown=False, injected_bytes=0, injected_tokens_estimate=0)
    else:
        n = len(injected_text(memory_dir).encode("utf-8"))
        out.update(memory_block_shown=True, skills_index_shown=True, memory_md_bytes=memory_md.stat().st_size if memory_md.exists() else 0,
                   injected_bytes=n, injected_tokens_estimate=n // BYTES_PER_TOKEN)
    return out


class ExposureHermes(LocalHermes):
    options_model = ExposureHermesOptions
    options: ExposureHermesOptions

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._memory_dir is None:
            raise ValueError("exposure arms need a memory (--memory)")
        self._exposure_report = report(self.options.exposure, self._memory_dir, self._memory_report["memory_sha256"])
        if self._exposure_report["injected_tokens_estimate"] > MAX_INJECTED_TOKENS:
            raise ValueError(f"exposure=all would inject about {self._exposure_report['injected_tokens_estimate']} tokens, "
                             f"over the {MAX_INJECTED_TOKENS} limit")

    @staticmethod
    def name() -> str:
        return "frontier-memory-hermes-exposure"

    def _actor_config(self, model: str) -> str:
        config = yaml.safe_load(super()._actor_config(model))
        config = apply_exposure(config, self.options.exposure, self._memory_dir)
        plugins = config.setdefault("plugins", {})
        enabled = plugins.setdefault("enabled", [])
        if not isinstance(enabled, list):
            raise ValueError("Hermes plugins.enabled must be a list")
        if OBSERVER_ID not in enabled:
            enabled.append(OBSERVER_ID)
        return yaml.safe_dump(config)

    async def exec_as_agent(self, environment, command, env=None, **kwargs):
        local_env = {
            **(env or {}),
            "FM_DELIVERY_MODE": "observe",
            "FM_DELIVERY_MEMORY_SHA256": self._memory_report["memory_sha256"],
            "FM_DELIVERY_MEMORY_ENABLED": "0" if self.options.exposure == "none" else "1",
        }
        return await super().exec_as_agent(environment, command, env=local_env, **kwargs)

    async def run(self, instruction, environment, context):
        report_path = self.logs_dir / "exposure-report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(self._exposure_report, indent=1) + "\n")
        upload_dir = environment.upload_dir

        async def filtered_upload_dir(source, target, *args, **kwargs):
            if skip_upload(self.options.exposure, str(target)):
                return None
            result = await upload_dir(source, target, *args, **kwargs)
            if str(target).rstrip("/") == MEMORIES_TARGET:
                plugin_source = Path(__file__).with_name("delivery_plugin")
                await upload_dir(plugin_source, OBSERVER_TARGET, *args, **kwargs)
            return result

        environment.upload_dir = filtered_upload_dir  # instance attribute; restored below
        try:
            return await super().run(instruction, environment, context)
        finally:
            del environment.upload_dir

    def populate_context_post_run(self, context) -> None:  # the trial's metadata carries the counts next to the digest
        super().populate_context_post_run(context)
        context.metadata = {**(context.metadata or {}), "fm_exposure": self._exposure_report}
