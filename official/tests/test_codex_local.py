"""Host-side checks for the local Codex relay wrapper."""

import asyncio
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "official"))
UPSTREAM = next(p for p in (REPO / "frontiermemory", REPO.parents[2] / "frontiermemory", REPO) if (p / "src").is_dir())
sys.path.insert(0, str(UPSTREAM / "src"))

from frontier_memory.agents.codex import MemoryCodex  # noqa: E402
from fm_local.codex_local import LocalCodex  # noqa: E402


def test_task_agent_gets_relay_and_placeholder(monkeypatch):
    seen = {}

    async def fake(self, environment, command, env=None, **kwargs):
        seen["env"] = env

    monkeypatch.setattr(MemoryCodex, "exec_as_agent", fake)
    monkeypatch.setenv("FM_LOCAL_BASE_URL", "http://10.0.2.2:1/v1")
    source = {"OPENAI_BASE_URL": "https://api.openai.com/v1", "OPENAI_API_KEY": "synthetic-real-key", "EXTRA": "kept"}
    asyncio.run(LocalCodex.exec_as_agent(object.__new__(LocalCodex), None, "codex", env=source))

    assert seen["env"] == {
        "OPENAI_BASE_URL": "http://10.0.2.2:1/v1",
        "OPENAI_API_KEY": "local-placeholder",
        "EXTRA": "kept",
    }
