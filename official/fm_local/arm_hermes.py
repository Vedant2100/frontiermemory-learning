"""Exploratory delivery arms (results/preregistration-arms.md): the HM task agent (LocalHermes) with only memory delivery
changed. Memory content is never edited; the rules live in arm_logic.py.

Load through the official hook: --harness fm_local.arm_hermes:ArmHermes --ak arm=<arm> [--ak corpus_dir=... evidence_map=...]

  readfirst    HM, plus one fixed sentence (READ_FIRST) through Hermes's `agent.system_prompt` key (as exposure=all uses it).
  scoped       HM, but the indexed skills directory gets only the top arm_logic.K_SCOPED memory skills by BM25 between the
               task instruction and each SKILL.md. The full memory folder is still uploaded to $HERMES_HOME/memories.
  categorized  HM, but memory skills are indexed under three fixed categories (Hermes's own category = parent folder, with a
               DESCRIPTION.md heading; agent/prompt_builder.py). Same skills, same files; only the index grouping changes.
  cue          Like exposure=none at start (memory block off, no memory skills indexed, folder uploaded), plus the fm-cue
               plugin (cue_plugin/), which appends a skill to a tool result when the call matches it.
  raw          No generated memory. The corpus's trajectory files are uploaded to $HERMES_HOME/records with a one-line pointer.
  evidence     As raw, but only the runs results/recency-check.json relates to this task (the coverage rule of
               scripts/corpus_coverage.py, which reproduces the benchmark's published coverage); a task with none gets nothing.

Each trial writes agent/arm-report.json: counts and digests only, never memory text, file names or corpus text.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Literal

import yaml

from frontier_memory.agents.hermes import ACTOR_HOME, MemoryHermesOptions

from fm_local import arm_logic
from fm_local.hermes_local import LocalHermes

SKILLS_TARGET = f"{ACTOR_HOME}/skills"
MEMORIES_TARGET = f"{ACTOR_HOME}/memories"
CONFIG_TARGET = f"{ACTOR_HOME}/config.yaml"
RECORDS_TARGET = arm_logic.RECORDS_TARGET
CUE_PLUGIN, READ_FIRST, POINTER = arm_logic.CUE_PLUGIN, arm_logic.READ_FIRST, arm_logic.POINTER
assert RECORDS_TARGET == f"{ACTOR_HOME}/records"
MEMORY_ARMS = {"readfirst", "scoped", "categorized", "cue"}


class ArmHermesOptions(MemoryHermesOptions):
    arm: Literal["readfirst", "scoped", "categorized", "cue", "raw", "evidence"]
    corpus_dir: str | None = None     # raw, evidence: the corpus's inputs/ folder
    evidence_map: str | None = None   # evidence: JSON {task: [file names]}


def sha(text: str | bytes) -> str:
    return hashlib.sha256(text.encode() if isinstance(text, str) else text).hexdigest()


build_skills_dir = arm_logic.build_skills_dir


class ArmHermes(LocalHermes):
    options_model = ArmHermesOptions
    options: ArmHermesOptions

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        arm = self.options.arm
        if arm in MEMORY_ARMS and self._memory_dir is None:
            raise ValueError(f"arm {arm} needs a memory (--memory)")
        if arm in ("raw", "evidence"):
            if self._memory_dir is not None:
                raise ValueError(f"arm {arm} replaces generated memory; run it without --memory")
            if not self.options.corpus_dir or not Path(self.options.corpus_dir).is_dir():
                raise ValueError(f"arm {arm} needs corpus_dir (the corpus inputs folder)")
            if arm == "evidence" and not (self.options.evidence_map and Path(self.options.evidence_map).is_file()):
                raise ValueError("arm evidence needs evidence_map")
        self._pointer = None
        self._report = {"arm": arm, "memory_sha256": (self._memory_report or {}).get("memory_sha256")}

    @staticmethod
    def name() -> str:
        return "frontier-memory-hermes-arm"

    def _actor_config(self, model: str) -> str:
        config = yaml.safe_load(super()._actor_config(model))
        agent = config.setdefault("agent", {})
        extra = READ_FIRST if self.options.arm == "readfirst" else self._pointer
        if extra:
            if agent.get("system_prompt"):
                raise ValueError("agent.system_prompt is already set; refusing to overwrite it")
            agent["system_prompt"] = extra
            self._report["system_prompt_sha256"] = sha(extra)
        if self.options.arm == "cue":
            config["memory"]["memory_enabled"] = False
            config["memory"]["user_profile_enabled"] = False
            enabled = config.setdefault("plugins", {}).setdefault("enabled", [])
            if CUE_PLUGIN not in enabled:
                enabled.append(CUE_PLUGIN)
        return yaml.safe_dump(config)

    async def exec_as_agent(self, environment, command, env=None, **kwargs):
        if self.options.arm == "cue":
            env = {**(env or {}), "FM_CUE_MEMORY": MEMORIES_TARGET, "FM_CUE_LOG": str(self.environment_logs_dir)}
        return await super().exec_as_agent(environment, command, env=env, **kwargs)

    def _records(self, task: str) -> list[Path]:
        inputs = Path(self.options.corpus_dir)
        if self.options.arm == "raw":
            return sorted(p for p in inputs.iterdir() if p.is_file())
        names = json.loads(Path(self.options.evidence_map).read_text()).get(task)
        if names is None:
            raise ValueError("task missing from evidence_map")
        return [inputs / n for n in names]

    async def run(self, instruction, environment, context):
        arm, report = self.options.arm, self._report
        upload_dir, upload_file = environment.upload_dir, environment.upload_file
        with tempfile.TemporaryDirectory(prefix="fm-arm-") as tmp:
            tmp = Path(tmp)
            skills_source = None
            if arm in ("scoped", "categorized"):
                found = arm_logic.skills(self._memory_dir)
                report["memory_skills"] = len(found)
                if arm == "scoped":
                    picks = arm_logic.bm25_select(instruction, found)
                    build_skills_dir(self._memory_dir, tmp / "skills", [(s["rel"], s["rel"]) for s in picks], {})
                    report.update(selected=len(picks), selected_sha256=[sha(s["text"])[:16] for s in picks],
                                  selected_scores=[s["score"] for s in picks])
                else:
                    cats = {s["rel"]: arm_logic.categorize(s) for s in found}
                    used = sorted(set(cats.values()))
                    build_skills_dir(self._memory_dir, tmp / "skills",
                                     [(s["rel"], f"{cats[s['rel']]}/{s['leaf']}") for s in found],
                                     {c: arm_logic.CATEGORIES[c][0] for c in used})
                    report["categories"] = {c: sum(v == c for v in cats.values()) for c in arm_logic.CATEGORIES}
                skills_source = tmp / "skills"
            if arm == "cue":
                plugin = tmp / CUE_PLUGIN
                shutil.copytree(Path(__file__).with_name("cue_plugin"), plugin)
                shutil.copyfile(Path(arm_logic.__file__), plugin / "arm_logic.py")
                report["memory_skills"] = len(arm_logic.skills(self._memory_dir))
            records = None
            if arm in ("raw", "evidence"):
                files = self._records(environment.environment_name)
                report.update(records=len(files), records_bytes=sum(p.stat().st_size for p in files))
                if files:
                    records = tmp / "records"
                    records.mkdir()
                    for p in files:
                        shutil.copyfile(p, records / p.name)
                    self._pointer = POINTER[arm].format(n=len(files), path=RECORDS_TARGET)

            async def arm_upload_dir(source, target, *a, **kw):
                target = str(target).rstrip("/")
                if target == SKILLS_TARGET and arm == "cue":
                    return None  # as exposure=none: memory skills stay out of the index
                if target == SKILLS_TARGET and skills_source is not None:
                    return await upload_dir(skills_source, target, *a, **kw)
                result = await upload_dir(source, target, *a, **kw)
                if target == MEMORIES_TARGET and arm == "cue":
                    await upload_dir(tmp / CUE_PLUGIN, f"{ACTOR_HOME}/plugins/{CUE_PLUGIN}", *a, **kw)
                return result

            async def arm_upload_file(source, target, *a, **kw):
                result = await upload_file(source, target, *a, **kw)
                if str(target) == CONFIG_TARGET and records is not None:
                    await upload_dir(records, RECORDS_TARGET, *a, **kw)
                return result

            path = self.logs_dir / "arm-report.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            environment.upload_dir, environment.upload_file = arm_upload_dir, arm_upload_file  # restored below
            try:
                return await super().run(instruction, environment, context)
            finally:
                del environment.upload_dir, environment.upload_file
                path.write_text(json.dumps(report, indent=1) + "\n")

    def populate_context_post_run(self, context) -> None:
        super().populate_context_post_run(context)
        context.metadata = {**(context.metadata or {}), "fm_arm": self._report}
