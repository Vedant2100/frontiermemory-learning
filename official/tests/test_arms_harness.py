"""Harness-level tests for the exploratory arms: the real adapter classes (Harbor 0.24.0, pinned frontier_memory) run
against a fake container that records uploads and commands. Skipped where those packages are not installed.

    python3 -m unittest official/tests/test_arms_harness.py    (from the repository root, in an env with harbor installed)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "official"))
sys.path.insert(0, str(REPO / "official/tests"))
os.environ.setdefault("FM_LOCAL_BASE_URL", "http://10.0.2.2:9999/v1")
try:
    from fm_local import arm_hermes, arm_logic, claude_code_local, codex_local, generator_hermes
    from frontier_memory import hermes_dream
except ImportError as exc:  # host without harbor: the guest runs these
    raise unittest.SkipTest(f"harbor/frontier_memory not importable: {exc}")
from test_arms import memory  # noqa: E402

MODEL = "openai/qwen3.8:27b-mtp-q4_K_M"


class FakeEnv:
    """Records uploads (with a listing of uploaded folders) and answers every command with success."""

    def __init__(self, task: str):
        self.environment_name, self.default_user, self.uploads, self.commands = task, None, [], []

    async def exec(self, command, **kw):
        self.commands.append((command, kw.get("env") or {}))
        return SimpleNamespace(return_code=0, stdout="", stderr="")

    async def upload_file(self, source, target, *a, **kw):
        self.uploads.append(("file", str(target), Path(source).read_text(errors="replace")))

    async def upload_dir(self, source, target, *a, **kw):
        files = sorted(p.relative_to(source).as_posix() for p in Path(source).rglob("*") if p.is_file())
        self.uploads.append(("dir", str(target).rstrip("/"), files))

    async def download_file(self, source, target, *a, **kw):
        Path(target).write_text(json.dumps({"system_prompt": "", "input_tokens": 1}) + "\n")


def run_arm(arm: str, mem: Path | None, logs: Path, task="build-word2vec-pipeline", **ak) -> tuple[FakeEnv, dict]:
    agent = arm_hermes.ArmHermes(logs_dir=logs, model_name=MODEL, arm=arm, memory_dir=str(mem) if mem else None,
                                 extra_env={"OPENAI_API_KEY": "local-placeholder"}, **ak)
    env = FakeEnv(task)
    asyncio.run(agent.run("Train word2vec and report cosine similarity metrics", env, SimpleNamespace(metadata=None,
                          n_input_tokens=None, n_cache_tokens=None, n_output_tokens=None)))
    config = yaml.safe_load(next(c for k, t, c in env.uploads if t.endswith("/config.yaml")))
    return env, config


class ArmHermesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.mem = memory(self.base / "m")

    def tearDown(self):
        self.tmp.cleanup()

    def dirs(self, env):
        return {t: files for k, t, files in env.uploads if k == "dir"}

    def test_readfirst(self):
        env, config = run_arm("readfirst", self.mem, self.base / "l")
        self.assertEqual(config["agent"]["system_prompt"], arm_logic.READ_FIRST)
        self.assertTrue(config["memory"]["memory_enabled"])
        self.assertIn("/tmp/hermes/skills", self.dirs(env))
        report = json.loads((self.base / "l/arm-report.json").read_text())
        self.assertEqual(report["arm"], "readfirst")

    def test_scoped_uploads_top_k_only(self):
        env, config = run_arm("scoped", self.mem, self.base / "l")
        skills = self.dirs(env)["/tmp/hermes/skills"]
        want = arm_logic.bm25_select("Train word2vec and report cosine similarity metrics", arm_logic.skills(self.mem))
        self.assertEqual(want[0]["rel"], "eval-metrics")
        self.assertEqual(sorted({f.rsplit("/", 1)[0] for f in skills if f.endswith("SKILL.md")}), sorted(s["rel"] for s in want))
        self.assertEqual(len(self.dirs(env)["/tmp/hermes/memories"]),  # the whole memory stays reachable
                         sum(p.is_file() for p in self.mem.rglob("*")))
        report = json.loads((self.base / "l/arm-report.json").read_text())
        self.assertEqual((report["memory_skills"], report["selected"]), (4, 3))
        self.assertNotIn("system_prompt", config["agent"])

    def test_categorized(self):
        env, _ = run_arm("categorized", self.mem, self.base / "l")
        skills = self.dirs(env)["/tmp/hermes/skills"]
        self.assertIn("memory-user-preferences/user-style/SKILL.md", skills)
        self.assertIn("memory-procedures/DESCRIPTION.md", skills)
        self.assertEqual(sum(f.endswith("SKILL.md") for f in skills), 4)

    def test_cue(self):
        env, config = run_arm("cue", self.mem, self.base / "l")
        dirs = self.dirs(env)
        self.assertNotIn("/tmp/hermes/skills", dirs)
        self.assertEqual(sorted(dirs["/tmp/hermes/plugins/fm-cue"]), ["__init__.py", "arm_logic.py", "plugin.yaml"])
        self.assertFalse(config["memory"]["memory_enabled"])
        self.assertIn("fm-cue", config["plugins"]["enabled"])
        envs = [e for c, e in env.commands if "hermes" in c and "chat" in c]
        self.assertTrue(envs and envs[0]["FM_CUE_MEMORY"] == "/tmp/hermes/memories")
        self.assertEqual(envs[0]["HERMES_CODEX_TTFB_TIMEOUT_SECONDS"], "900")  # LocalHermes watchdogs kept

    def test_records_arms(self):
        corpus = self.base / "inputs"
        corpus.mkdir()
        for i in range(5):
            (corpus / f"t{i:04d}.json").write_text("{}")
        emap = self.base / "map.json"
        emap.write_text(json.dumps({"build-word2vec-pipeline": ["t0001.json", "t0003.json"], "cattrs-x": []}))
        env, config = run_arm("raw", None, self.base / "r", corpus_dir=str(corpus))
        self.assertEqual(len(self.dirs(env)["/tmp/hermes/records"]), 5)
        self.assertEqual(config["agent"]["system_prompt"], arm_logic.POINTER["raw"].format(n=5, path="/tmp/hermes/records"))
        self.assertFalse(config["memory"]["memory_enabled"])
        order = [t for _, t, _ in env.uploads]
        self.assertLess(order.index("/tmp/hermes/config.yaml"), order.index("/tmp/hermes/records"))
        env, config = run_arm("evidence", None, self.base / "e", corpus_dir=str(corpus), evidence_map=str(emap))
        self.assertEqual(self.dirs(env)["/tmp/hermes/records"], ["t0001.json", "t0003.json"])
        env, config = run_arm("evidence", None, self.base / "c", task="cattrs-x", corpus_dir=str(corpus), evidence_map=str(emap))
        self.assertNotIn("/tmp/hermes/records", self.dirs(env))
        self.assertNotIn("system_prompt", config["agent"])

    def test_refusals(self):
        with self.assertRaises(ValueError):
            arm_hermes.ArmHermes(logs_dir=self.base / "x", model_name=MODEL, arm="scoped")
        with self.assertRaises(ValueError):
            arm_hermes.ArmHermes(logs_dir=self.base / "x", model_name=MODEL, arm="raw", memory_dir=str(self.mem),
                                 corpus_dir=str(self.base))
        with self.assertRaises(Exception):
            arm_hermes.ArmHermes(logs_dir=self.base / "x", model_name=MODEL, arm="bogus", memory_dir=str(self.mem))


class GeneratorTests(unittest.TestCase):
    def test_wrapper_sets_request(self):
        self.assertTrue(generator_hermes.REQUEST.startswith(hermes_dream.LEARN_REQUEST))
        ns: dict = {}
        code = generator_hermes.GENERATOR_WRAPPER.replace("sys.exit(hermes_dream.main())", "")
        saved = sys.modules.pop("hermes_dream", None)
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "hermes_dream.py").write_text(Path(hermes_dream.__file__).read_text())
            exec(compile(code, str(Path(tmp, "driver.py")), "exec"), {"__file__": str(Path(tmp, "driver.py")), **ns})
            sys.path.remove(tmp)
            mod = sys.modules.pop("hermes_dream")
        if saved is not None:
            sys.modules["hermes_dream"] = saved
        self.assertEqual(mod.LEARN_REQUEST, generator_hermes.REQUEST)

    def test_install_uploads_generator_driver(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = generator_hermes.GeneratorHermesLearn(logs_dir=Path(tmp), model_name=MODEL)
            env = FakeEnv("dream")
            asyncio.run(agent.install(env))
            drivers = [c for k, t, c in env.uploads if t.endswith("/driver.py")]
            self.assertEqual(drivers[-1], generator_hermes.GENERATOR_WRAPPER)


class ApiHarnessTests(unittest.TestCase):
    def test_codex_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = codex_local.LocalCodex(logs_dir=Path(tmp), model_name=MODEL)
            config = agent._build_effective_config(None)
            self.assertEqual(config["model_provider"], "fmlocal")
            p = config["model_providers"]["fmlocal"]
            self.assertEqual((p["base_url"], p["wire_api"], p["stream_idle_timeout_ms"], p["env_key"]),
                             (os.environ["FM_LOCAL_BASE_URL"], "responses", 900_000, "OPENAI_API_KEY"))
            self.assertTrue(config["features"]["memories"])  # official MemoryCodex setting kept

    def test_claude_code_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = claude_code_local.LocalClaudeCode(logs_dir=Path(tmp), model_name="anthropic/qwen3.8:27b-mtp-q4_K_M")
            self.assertEqual(agent._resolved_model_name(), "qwen3.8:27b-mtp-q4_K_M")
            env = agent._resolve_auth_env()
            self.assertEqual(env, {"ANTHROPIC_API_KEY": "local-placeholder", "ANTHROPIC_BASE_URL": "http://10.0.2.2:9999"})


if __name__ == "__main__":
    unittest.main()
