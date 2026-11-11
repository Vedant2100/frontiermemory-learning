"""Harness-level test for the blend arm: the real BlendHermes class (Harbor, pinned frontier_memory) against a fake container.
Skipped where those packages are not installed (the guest runs it).

    python3 -m unittest official/tests/test_blend_harness.py    (from the repository root, in an env with harbor installed)
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

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "official"))
os.environ.setdefault("FM_LOCAL_BASE_URL", "http://10.0.2.2:9999/v1")
try:
    from fm_local import blend_hermes, blend_logic as B
except ImportError as exc:  # host without harbor
    raise unittest.SkipTest(f"harbor/frontier_memory not importable: {exc}")

MODEL = "openai/qwen3.8:27b-mtp-q4_K_M"
ORIG = "Train word2vec on `/app/c.txt` and report 3 similarities within 20 min."
BLEND = ORIG + " Check the vocabulary size first."


class FakeEnv:
    def __init__(self, task):
        self.environment_name, self.default_user, self.uploads, self.commands = task, None, [], []

    async def exec(self, command, **kw):
        self.commands.append((command, kw.get("env") or {}))
        return SimpleNamespace(return_code=0, stdout="", stderr="")

    async def upload_file(self, source, target, *a, **kw):
        self.uploads.append((str(target), Path(source).read_text(errors="replace")))

    async def upload_dir(self, source, target, *a, **kw):
        self.uploads.append((str(target), ""))

    async def download_file(self, source, target, *a, **kw):
        Path(target).write_text(json.dumps({"system_prompt": "", "input_tokens": 1}) + "\n")


def run_blend(bmap, task, instruction, logs, **kw):
    agent = blend_hermes.BlendHermes(logs_dir=logs, model_name=MODEL, arm="blend", blend_map=str(bmap),
                                     extra_env={"OPENAI_API_KEY": "local-placeholder"}, **kw)
    env = FakeEnv(task)
    asyncio.run(agent.run(instruction, env, SimpleNamespace(metadata=None, n_input_tokens=None, n_cache_tokens=None,
                                                            n_output_tokens=None)))
    return env, json.loads((logs / "arm-report.json").read_text())


def everything(env) -> str:
    return json.dumps([env.commands, env.uploads])


class BlendHermesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.map = self.base / "map.json"
        self.map.write_text(json.dumps({
            "t1": {"ok": True, "blend": BLEND, "blend_sha": B.sha(BLEND), "orig_sha": B.sha(ORIG), "rolls": 1, "added_sentences": 1},
            "t2": {"ok": False, "blend": None, "orig_sha": B.sha(ORIG), "rolls": 2}}))

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_agent_gets_the_rewritten_task(self):
        env, report = run_blend(self.map, "t1", ORIG, self.base / "l")
        self.assertIn("Check the vocabulary size first.", everything(env))
        self.assertEqual((report["arm"], report["blended"], report["blend_sha256"]), ("blend", True, B.sha(BLEND)))
        self.assertNotIn("Check the vocabulary", (self.base / "l/arm-report.json").read_text())  # report holds no text

    def test_a_failed_rewrite_runs_the_original(self):
        env, report = run_blend(self.map, "t2", ORIG, self.base / "l")
        self.assertNotIn("Check the vocabulary size first.", everything(env))
        self.assertEqual((report["blended"], report["blend_sha256"]), (False, B.sha(ORIG)))

    def test_changed_task_or_memory_option_is_refused(self):
        with self.assertRaises(ValueError):
            run_blend(self.map, "t1", ORIG + " changed", self.base / "l")
        with self.assertRaises(ValueError):
            run_blend(self.map, "t3", ORIG, self.base / "l")
        with self.assertRaises(ValueError):
            blend_hermes.BlendHermes(logs_dir=self.base / "l2", model_name=MODEL, arm="blend", blend_map=str(self.map),
                                     memory_dir=str(self.base), extra_env={"OPENAI_API_KEY": "x"})

    def test_no_memory_is_uploaded(self):
        env, _ = run_blend(self.map, "t1", ORIG, self.base / "l")
        self.assertFalse([t for t, _ in env.uploads if "/skills" in t or "/memories" in t])


if __name__ == "__main__":
    unittest.main()
