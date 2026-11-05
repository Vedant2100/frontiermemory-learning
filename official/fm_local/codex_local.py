"""Local Ollama relay wrapper around FrontierMemory's pinned Codex adapter."""

from __future__ import annotations

import os

from frontier_memory.agents.codex import MemoryCodex

PLACEHOLDER_API_KEY = "local-placeholder"


def base_url() -> str:
    return os.environ["FM_LOCAL_BASE_URL"]


class LocalCodex(MemoryCodex):
    """Official Codex memory behavior, with model calls routed only to the relay."""

    async def exec_as_agent(self, environment, command, env=None, **kwargs):
        local_env = {
            **(env or {}),
            "OPENAI_BASE_URL": base_url(),
            "OPENAI_API_KEY": PLACEHOLDER_API_KEY,
        }
        return await super().exec_as_agent(environment, command, env=local_env, **kwargs)
