"""Official Claude Code task agent (frontier_memory.agents.claude_code:MemoryClaudeCode) with model calls sent to our
local server, which speaks the Anthropic Messages API (Ollama 0.40.11, through the relay).

The base URL and model are set where Harbor 0.24.0 resolves them (_resolve_auth_env, _resolved_model_name), so Harbor's own
rule applies: with a custom base URL it pins ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL and CLAUDE_CODE_SUBAGENT_MODEL to
the same model, and background calls cannot ask for a Claude model the server does not have. API_TIMEOUT_MS is 1800 s,
Hermes's per-call limit in the other arms (hermes_local.WATCHDOGS); Claude Code's default is 600 s. The agent key is the
placeholder; no OAuth token is passed. Memory loading is untouched (Claude Code auto-memory, MEMORY.md first).

Load through the official hook: --harness fm_local.claude_code_local:LocalClaudeCode
"""

from __future__ import annotations

import os

from frontier_memory.agents.claude_code import MemoryClaudeCode

PLACEHOLDER = "local-placeholder"
API_TIMEOUT_MS = "1800000"


def messages_base_url() -> str:
    """Claude Code appends /v1/messages to its base URL; FM_LOCAL_BASE_URL ends in /v1."""
    base = os.environ["FM_LOCAL_BASE_URL"].rstrip("/")
    return base.removesuffix("/v1")


class LocalClaudeCode(MemoryClaudeCode):
    @staticmethod
    def name() -> str:
        return "frontier-memory-claude-code-local"

    def _resolved_model_name(self) -> str | None:
        return (self.model_name or "").split("/", 1)[-1] or None  # -m anthropic/<local model> -> <local model>

    def _resolve_auth_env(self) -> dict[str, str]:
        return {"ANTHROPIC_API_KEY": PLACEHOLDER, "ANTHROPIC_BASE_URL": messages_base_url()}

    async def exec_as_agent(self, environment, command, env=None, **kwargs):
        return await super().exec_as_agent(environment, command, env={**(env or {}), "API_TIMEOUT_MS": API_TIMEOUT_MS},
                                           **kwargs)
