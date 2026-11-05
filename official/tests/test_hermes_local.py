"""Host-side tests for fm_local.hermes_local: the model URL and watchdog settings reach every agent command (D100).

Run: .venv/bin/python -m pytest -q official/tests/test_hermes_local.py   (from the repo root)
"""

import asyncio
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "official"))
UPSTREAM = next(p for p in (REPO / "frontiermemory", REPO.parents[2] / "frontiermemory") if (p / "src").is_dir())
sys.path.insert(0, str(UPSTREAM / "src"))

from frontier_memory.agents.hermes import HermesLearn, MemoryHermes  # noqa: E402
from fm_local import hermes_local as hl  # noqa: E402


def run(cls, parent, monkeypatch, env):
    seen = {}

    async def fake(self, environment, command, env=None, **kwargs):
        seen["env"] = env

    monkeypatch.setattr(parent, "exec_as_agent", fake)
    monkeypatch.setenv("FM_LOCAL_BASE_URL", "http://10.0.2.2:1/v1")
    asyncio.run(cls.exec_as_agent(object.__new__(cls), None, "hermes", env=env))
    return seen["env"]


def test_task_agent_gets_url_and_watchdogs(monkeypatch):
    env = run(hl.LocalHermes, MemoryHermes, monkeypatch, {"OPENAI_BASE_URL": "https://api.openai.com/v1", "X": "1"})
    assert env["OPENAI_BASE_URL"] == "http://10.0.2.2:1/v1" and env["X"] == "1"
    assert {k: env[k] for k in hl.WATCHDOGS} == hl.WATCHDOGS


def test_task_agent_without_env(monkeypatch):
    assert run(hl.LocalHermes, MemoryHermes, monkeypatch, None) == hl.WATCHDOGS


def test_generator_gets_url_and_watchdogs(monkeypatch):
    env = run(hl.LocalHermesLearn, HermesLearn, monkeypatch, None)
    assert env == {"FM_LOCAL_BASE_URL": "http://10.0.2.2:1/v1", **hl.WATCHDOGS}


def test_watchdog_values():
    assert hl.WATCHDOGS == {"HERMES_CODEX_TTFB_TIMEOUT_SECONDS": "900", "HERMES_CODEX_EVENT_STALE_TIMEOUT_SECONDS": "900",
                            "HERMES_API_CALL_STALE_TIMEOUT": "1800"}
