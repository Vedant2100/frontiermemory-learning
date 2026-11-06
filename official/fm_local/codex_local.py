"""Official Codex task agent (frontier_memory.agents.codex:MemoryCodex) with model calls sent to our local server.

Codex CLI 0.160.1's built-in `openai` provider has a 300 s stream idle timeout that config cannot change ("Built-in
provider IDs (openai, ollama, and lmstudio) are reserved and cannot be overridden"; stream_idle_timeout_ms default 300000,
Codex config reference). That is the same 300 s cut that made Hermes give up in gate 1 (D100). So calls go through one
custom provider, `fmlocal`, pointing at the relay with the Responses wire API and a 900 s idle limit, the value the Hermes
arms use (hermes_local.WATCHDOGS). Retry counts stay at Codex's defaults. The agent key is the placeholder.
Memory loading is untouched: MemoryCodex seeds $CODEX_HOME/memories and turns the memories feature on in every run.

Load through the official hook: --harness fm_local.codex_local:LocalCodex
"""

from __future__ import annotations

import os

from frontier_memory.agents.codex import MemoryCodex

PROVIDER = "fmlocal"
STREAM_IDLE_TIMEOUT_MS = 900_000


def provider_config(base_url: str) -> dict:
    return {"model_provider": PROVIDER,
            "model_providers": {PROVIDER: {"name": "FrontierMemory local relay", "base_url": base_url,
                                           "env_key": "OPENAI_API_KEY", "wire_api": "responses",
                                           "stream_idle_timeout_ms": STREAM_IDLE_TIMEOUT_MS}}}


class LocalCodex(MemoryCodex):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, value in provider_config(os.environ["FM_LOCAL_BASE_URL"]).items():
            if key in self._base_config and self._base_config[key] != value:
                raise ValueError(f"Codex config already sets {key}; refusing to overwrite it")
            self._base_config[key] = value

    @staticmethod
    def name() -> str:
        return "frontier-memory-codex-local"

    async def exec_as_agent(self, environment, command, env=None, **kwargs):
        return await super().exec_as_agent(environment, command, env={**(env or {}), "OPENAI_API_KEY": "local-placeholder"},
                                           **kwargs)
