"""Host-side checks for the local Claude Code Messages relay wrapper."""

import asyncio
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "official"))
UPSTREAM = next(p for p in (REPO / "frontiermemory", REPO.parents[2] / "frontiermemory", REPO) if (p / "src").is_dir())
sys.path.insert(0, str(UPSTREAM / "src"))

from frontier_memory.agents.claude_code import MemoryClaudeCode  # noqa: E402
from fm_local.claude_code_local import LocalClaudeCode  # noqa: E402


def test_task_agent_gets_messages_relay_and_placeholder_credentials(monkeypatch):
    seen = {}

    async def fake(self, environment, command, env=None, **kwargs):
        seen["env"] = env

    monkeypatch.setattr(MemoryClaudeCode, "exec_as_agent", fake)
    monkeypatch.setenv("FM_LOCAL_BASE_URL", "http://10.0.2.2:1/v1")
    monkeypatch.setenv("FM_LOCAL_MODEL", "qwen3.8:27b-mtp-q4_K_M")
    source = {
        "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
        "ANTHROPIC_MODEL": "vendor-model",
        "ANTHROPIC_API_KEY": "synthetic-real-key",
        "ANTHROPIC_AUTH_TOKEN": "synthetic-real-token",
        "EXTRA": "kept",
    }
    asyncio.run(LocalClaudeCode.exec_as_agent(object.__new__(LocalClaudeCode), None, "claude", env=source))

    assert seen["env"] == {
        "ANTHROPIC_BASE_URL": "http://10.0.2.2:1",
        "ANTHROPIC_MODEL": "qwen3.8:27b-mtp-q4_K_M",
        "ANTHROPIC_API_KEY": "local-placeholder",
        "ANTHROPIC_AUTH_TOKEN": "local-placeholder",
        "EXTRA": "kept",
    }
