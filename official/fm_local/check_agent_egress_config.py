#!/usr/bin/env python3
"""Validate and remove a private Harbor --print-config result; emit counts only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

EXPECTED_ADAPTERS = {
    "codex": "fm_local.codex_local:LocalCodex",
    "claude-code": "fm_local.claude_code_local:LocalClaudeCode",
}
MODEL = "qwen3.8:27b-mtp-q4_K_M"


def main() -> int:
    if (len(sys.argv) != 4 or sys.argv[2] not in EXPECTED_ADAPTERS
            or sys.argv[3] not in ("docker", "modal")):
        print("HARNESS_EGRESS_CONFIG_PREFLIGHT_FAILED arguments")
        return 2
    path = Path(sys.argv[1])
    try:
        config = json.loads(path.read_text())
    except (OSError, ValueError, TypeError):
        print("HARNESS_EGRESS_CONFIG_PREFLIGHT_FAILED config_unreadable")
        return 1
    finally:
        path.unlink(missing_ok=True)

    agents = config.get("agents") or []
    agent = agents[0] if len(agents) == 1 else {}
    agent_hosts = agent.get("extra_allowed_hosts") or []
    environment_present = "environment" in config
    environment_config = config.get("environment")
    environment_config_valid = (
        not environment_present
        or (isinstance(environment_config, dict)
            and environment_config.get("type") == sys.argv[3])
    )
    if not isinstance(environment_config, dict):
        environment_config = {}
    environment_hosts = environment_config.get("extra_allowed_hosts") or []
    verifier_env = (config.get("verifier") or {}).get("env") or {}
    verifier_key = str(verifier_env.get("ANTHROPIC_API_KEY", ""))

    checks = {
        "one_agent": len(agents) == 1,
        "expected_adapter": agent.get("import_path") == EXPECTED_ADAPTERS[sys.argv[2]],
        "local_model": str(agent.get("model_name") or "").endswith(MODEL),
        "docker_environment": (
            sys.argv[3] == "docker" and environment_config_valid
        ),
        "agent_allowlist": set(agent_hosts) == {"10.0.2.2"},
        "environment_allowlist_empty": not environment_hosts,
        "verifier_key_template": "JUDGE_ANTHROPIC_KEY" in verifier_key,
    }
    print(
        "HARNESS_EGRESS_CONFIG_PREFLIGHT "
        f"passed={int(all(checks.values()))} agent_hosts={len(agent_hosts)} "
        f"environment_hosts={len(environment_hosts)} checks={sum(checks.values())}/{len(checks)}"
    )
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
