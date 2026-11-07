"""The system prompt Hermes sends on each model call, rebuilt from a finished trial's saved files (D125, D126).

Hermes saves its cached system prompt in agent/hermes-session.jsonl. The config key `agent.system_prompt` is its ephemeral
system prompt: Hermes appends it to the system message at API-call time only and never saves it (pinned Hermes d923a5eb:
hermes_cli/cli_init_mixin.py takes HERMES_EPHEMERAL_SYSTEM_PROMPT, else personality.py resolve_ephemeral_system_prompt;
agent/turn_context.py builds `(saved + "\\n\\n" + ephemeral).strip()`). A `display.personality` would replace the key, so a
config with one is refused here; neither the official adapter nor fm_local sets it or the environment variable.
The config is read from agent/hermes-config.yaml, the copy the adapter uploads as $HERMES_HOME/config.yaml.
Needs PyYAML (the guest's system Python has it). Returns text for the callers to search; prints nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml


def saved_prompt(trial: Path) -> str | None:
    p = Path(trial) / "agent" / "hermes-session.jsonl"
    if not p.is_file():
        return None
    with open(p, errors="replace") as f:
        return json.loads(f.readline()).get("system_prompt")


def ephemeral(trial: Path) -> str:
    """The config's agent.system_prompt ('' if unset). Raises ValueError if the config is missing or sets a personality."""
    p = Path(trial) / "agent" / "hermes-config.yaml"
    if not p.is_file():
        raise ValueError("no hermes-config.yaml")
    cfg = yaml.safe_load(p.read_text()) or {}
    if (cfg.get("display") or {}).get("personality"):
        raise ValueError("config sets display.personality, which would replace agent.system_prompt")
    return str((cfg.get("agent") or {}).get("system_prompt") or "")


def api_prompt(trial: Path) -> str | None:
    """Saved prompt plus the ephemeral one, as Hermes joins them for each call; None without a session file."""
    sp = saved_prompt(trial)
    if sp is None:
        return None
    extra = ephemeral(trial)
    return (sp + "\n\n" + extra).strip() if extra else sp
