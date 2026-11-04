"""Test-only agent (never used in counted runs): through the task's network policy, how long can a request wait
before the server's first byte, or between bytes, before something in the path cuts it?

    harbor run -p <memory task> -a fm_local.slow_probe:SlowProbe --allow-agent-host 10.0.2.2 --ak base=http://10.0.2.2:PORT
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any, override

from frontier_memory.agents.probe import NetworkProbe
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

CASES = ["first/5", "first/20", "first/40", "first/70", "idle/40", "idle/70"]
# POST cases (path, JSON body), as Hermes sends them; err/N makes the server answer 500 after N s.
POSTS = [("first/20", '{"stream":true}'), ("first/70", '{"stream":true}'), ("first/70", '{"stream":false}'),
         ("err/3", '{"stream":true}'), ("err/20", '{"stream":true}')]


class SlowProbe(NetworkProbe):
    def __init__(self, *args: Any, base: str = "", **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._base = base

    @staticmethod
    @override
    def name() -> str:
        return "fm-slow-probe"

    @override
    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        out = {}
        for case in CASES:
            url = f"{self._base}/{case}"
            r = await environment.exec(
                f"s=$(date +%s); c=$(curl -sS -o /dev/null -w '%{{http_code}}' --max-time 120 {shlex.quote(url)} 2>&1); "
                f"echo \"$c elapsed=$(( $(date +%s) - s ))s\"", timeout_sec=180)
            out[case] = (r.stdout or "").strip()[-160:]
        for case, body in POSTS:
            url = f"{self._base}/{case}/v1/responses"
            cmd = ("s=$(date +%s); curl -sS -o /tmp/pb -w '%{http_code}' --max-time 120 -H 'Content-Type: application/json' "
                   f"-d {shlex.quote(body)} {shlex.quote(url)} >/tmp/pc 2>/tmp/pe; e=$?; "
                   'echo "exit=$e code=$(cat /tmp/pc) elapsed=$(( $(date +%s) - s ))s '
                   'body=$(head -c 120 /tmp/pb | tr \'\\n\' \' \') err=$(head -c 90 /tmp/pe)"')
            r = await environment.exec(cmd, timeout_sec=180)
            out[f"POST {case} {body}"] = (r.stdout or "").strip()[-260:]
        path = Path(self.logs_dir) / "slow-probe.json"
        path.write_text(json.dumps(out, indent=1))
        await environment.exec("printf 'probe\\n' > /memory/MEMORY.md", timeout_sec=30)
