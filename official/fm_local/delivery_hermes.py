"""Hermes loader variants that keep the official generator and memory bytes fixed."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Literal

import yaml

from frontier_memory.agents.hermes import ACTOR_HOME, MemoryHermesOptions
from fm_local.hermes_local import LocalHermes

PLUGIN_ID = "fm-delivery-c2"
SKILLS_TARGET = f"{ACTOR_HOME}/skills"
MEMORIES_TARGET = f"{ACTOR_HOME}/memories"
PLUGIN_TARGET = f"{ACTOR_HOME}/plugins/{PLUGIN_ID}"
MAX_FRONTMATTER_BYTES = 64 * 1024


class DeliveryOptions(MemoryHermesOptions):
    delivery: Literal["cue", "scoped", "categorized"]


def _metadata(path: Path) -> dict:
    """Read bounded SKILL.md YAML frontmatter; malformed metadata yields an empty mapping."""
    try:
        raw = path.read_bytes()[:MAX_FRONTMATTER_BYTES].decode("utf-8")
        if not raw.startswith("---\n"):
            return {}
        end = raw.find("\n---", 4)
        if end < 0:
            return {}
        value = yaml.safe_load(raw[4:end])
        return value if isinstance(value, dict) else {}
    except (OSError, UnicodeError, yaml.YAMLError):
        return {}


def _tokens(text: str) -> set[str]:
    import re
    stop = {"about", "after", "also", "and", "are", "for", "from", "into", "that", "the", "this", "with", "your"}
    return {t for t in re.findall(r"[a-z0-9]+", text.casefold()) if len(t) >= 4 and t not in stop}


def skill_files(memory_dir: Path) -> list[Path]:
    return sorted((p for p in memory_dir.glob("skills/**/SKILL.md") if p.is_file()),
                  key=lambda p: p.relative_to(memory_dir).as_posix())


def selected_skill_tree_files(selected: list[Path], all_skills: list[Path]) -> list[Path]:
    """Include companions for selected skills while excluding nested unselected skills."""
    selected_roots = {path.parent for path in selected}
    all_roots = {path.parent for path in all_skills}
    files = set()
    for root in selected_roots:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            nested_skill_roots = {other for other in all_roots if other != root and other in path.parents}
            if nested_skill_roots:
                continue  # a selected nested skill is copied from its own root below
            files.add(path)
    return sorted(files, key=lambda p: p.as_posix())


def scoped_skills(memory_dir: Path, instruction: str) -> list[Path]:
    """Select skills by deterministic lexical overlap between their own metadata and the task instruction."""
    task = _tokens(instruction)
    selected = []
    for path in skill_files(memory_dir):
        meta = _metadata(path)
        scope_fields = ("scope", "repository", "repo", "domain", "task_family", "task", "project")
        declared = " ".join(str(meta.get(k, "")) for k in scope_fields if meta.get(k) is not None)
        evidence = declared or " ".join(str(meta.get(k, "")) for k in ("name", "description") if meta.get(k) is not None)
        overlap = len(task & _tokens(evidence))
        if overlap >= 2:
            selected.append(path)
    return selected


def category(path: Path) -> str:
    meta = _metadata(path)
    text = " ".join(str(meta.get(k, "")) for k in ("name", "description", "scope", "domain", "task_family")).casefold()
    if any(word in text for word in ("preference", "prefer", "writing style", "tone", "format preference")):
        return "User preferences"
    if any(word in text for word in ("environment", "version", "dependency", "repository", "toolchain", "configuration")):
        return "Environment facts"
    return "Procedural skills"


class DeliveryHermes(LocalHermes):
    options_model = DeliveryOptions
    options: DeliveryOptions
    delivery_mode = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._memory_dir is None:
            raise ValueError("delivery arms require a validated memory (--memory)")
        if self.options.delivery != self.delivery_mode:
            raise ValueError(f"expected delivery={self.delivery_mode}")
        self._delivery_report = {
            "delivery": self.delivery_mode,
            "memory_sha256": self._memory_report["memory_sha256"],
            "memory_files": len([p for p in self._memory_dir.rglob("*") if p.is_file()]),
            "skill_files": len(skill_files(self._memory_dir)),
            "memory_md_bytes": (self._memory_dir / "MEMORY.md").stat().st_size if (self._memory_dir / "MEMORY.md").is_file() else 0,
        }

    @staticmethod
    def name() -> str:
        return "frontier-memory-hermes-delivery"

    def _actor_config(self, model: str) -> str:
        config = yaml.safe_load(super()._actor_config(model))
        if self.delivery_mode == "cue":
            memory = config.setdefault("memory", {})
            memory["memory_enabled"] = False
            memory["user_profile_enabled"] = False
        if self.delivery_mode in {"cue", "scoped", "categorized"}:
            plugins = config.setdefault("plugins", {})
            enabled = plugins.setdefault("enabled", [])
            if not isinstance(enabled, list):
                raise ValueError("Hermes plugins.enabled must be a list")
            if PLUGIN_ID not in enabled:
                enabled.append(PLUGIN_ID)
        return yaml.safe_dump(config)

    def _write_report(self) -> None:
        path = self.logs_dir / "delivery-report.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._delivery_report, sort_keys=True) + "\n")

    async def exec_as_agent(self, environment, command, env=None, **kwargs):
        local_env = {
            **(env or {}),
            "FM_DELIVERY_MODE": self.delivery_mode,
            "FM_DELIVERY_MEMORY_SHA256": self._memory_report["memory_sha256"],
            "FM_DELIVERY_MEMORY_ENABLED": "0" if self.delivery_mode == "cue" else "1",
        }
        return await super().exec_as_agent(environment, command, env=local_env, **kwargs)

    async def run(self, instruction, environment, context):
        self._write_report()
        upload_dir = environment.upload_dir
        temp_root = Path(tempfile.mkdtemp(prefix="fm-delivery-", dir=self.logs_dir))
        plugin_source = Path(__file__).with_name("delivery_plugin")
        chosen = scoped_skills(self._memory_dir, str(instruction)) if self.delivery_mode == "scoped" else []
        all_skills = skill_files(self._memory_dir)
        selected = chosen if self.delivery_mode == "scoped" else ([] if self.delivery_mode == "cue" else all_skills)
        selected_files = selected_skill_tree_files(selected, all_skills)
        self._delivery_report["skills_selected"] = len(selected)
        self._delivery_report["skills_selected_files"] = len(selected_files)
        self._delivery_report["skills_selected_bytes"] = sum(p.stat().st_size for p in selected_files)
        self._delivery_report["skills_index_filtered"] = self.delivery_mode in {"cue", "scoped"}
        self._write_report()

        async def delivery_upload(source, target, *args, **kwargs):
            target = str(target).rstrip("/")
            if self.delivery_mode == "cue" and target == SKILLS_TARGET:
                self._delivery_report["skills_index_filtered"] = True
                self._write_report()
                return None
            if self.delivery_mode == "scoped" and target == SKILLS_TARGET:
                filtered = temp_root / "skills"
                filtered.mkdir(exist_ok=True)
                for source_file in selected_files:
                    rel = source_file.relative_to(self._memory_dir / "skills")
                    dest = filtered / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_file, dest)
                self._delivery_report["skills_index_filtered"] = True
                self._write_report()
                return await upload_dir(filtered, target, *args, **kwargs)
            result = await upload_dir(source, target, *args, **kwargs)
            if target == MEMORIES_TARGET:
                await upload_dir(plugin_source, PLUGIN_TARGET, *args, **kwargs)
            return result

        environment.upload_dir = delivery_upload
        try:
            result = await super().run(instruction, environment, context)
        finally:
            del environment.upload_dir
            shutil.rmtree(temp_root, ignore_errors=True)
        return result

    def populate_context_post_run(self, context) -> None:
        super().populate_context_post_run(context)
        context.metadata = {**(context.metadata or {}), "fm_delivery": self._delivery_report}


class CueHermes(DeliveryHermes):
    delivery_mode = "cue"


class ScopedHermes(DeliveryHermes):
    delivery_mode = "scoped"


class CategorizedHermes(DeliveryHermes):
    delivery_mode = "categorized"
