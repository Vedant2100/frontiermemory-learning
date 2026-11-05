"""Local Ollama Messages API wrapper around FrontierMemory's pinned Claude Code adapter."""

from __future__ import annotations

import os

from frontier_memory.agents.claude_code import MemoryClaudeCode

PLACEHOLDER_API_KEY = "local-placeholder"


def messages_base_url() -> str:
    """Claude Code expects the server root; its client appends /v1/messages."""
    base = os.environ["FM_LOCAL_BASE_URL"].rstrip("/")
    return base[:-3] if base.endswith("/v1") else base


def model_name() -> str:
    return os.environ["FM_LOCAL_MODEL"]


class LocalClaudeCode(MemoryClaudeCode):
    """Official Claude Code memory behavior, routed to the local Anthropic-compatible relay."""

    async def exec_as_agent(self, environment, command, env=None, **kwargs):
        local_env = {
            **(env or {}),
            "ANTHROPIC_BASE_URL": messages_base_url(),
            "ANTHROPIC_MODEL": model_name(),
            # Claude Code accepts either variable. Keep both placeholders so neither can
            # inherit a real verifier credential from the Harbor process environment.
            "ANTHROPIC_API_KEY": PLACEHOLDER_API_KEY,
            "ANTHROPIC_AUTH_TOKEN": PLACEHOLDER_API_KEY,
        }
        return await super().exec_as_agent(environment, command, env=local_env, **kwargs)
