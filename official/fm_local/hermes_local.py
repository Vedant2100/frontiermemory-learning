"""Official Hermes adapters with two changes: model calls go to our local server (protocol v4), and
Hermes's model-call watchdogs get local-server patience (D100).

The upstream adapters hard-code the OpenAI URL, so these subclasses replace that URL and nothing else.
FM_LOCAL_BASE_URL is the server's URL as seen from the task container.

WATCHDOGS: at effort max Hermes cancels a Responses call after 300 s without a stream event
(HIGH_EFFORT_SILENCE_FLOOR_SECONDS) and gives up after 5 such calls in a row. A local 27B model reading a
long prompt can be silent longer (gate 305865: customer delivery gave up). These set the first-event and
silence limits to 900 s, the value Hermes itself gives local servers for the first event, and the per-call
stale limit to 1800 s, Hermes's own per-call socket timeout. Explicit values, so they hold whichever path
Hermes takes.
Load through the official hook: --harness fm_local.hermes_local:LocalHermes (or :LocalHermesLearn).
"""

from __future__ import annotations

import os
from pathlib import Path

from frontier_memory import hermes_dream
from frontier_memory.agents.hermes import REMOTE, HermesLearn, MemoryHermes

WRAPPER = '''import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hermes_dream
official_route = hermes_dream.provider_route
def provider_route(model):
    return {**official_route(model), "base_url": os.environ["FM_LOCAL_BASE_URL"]}
hermes_dream.provider_route = provider_route
sys.exit(hermes_dream.main())
'''


WATCHDOGS = {"HERMES_CODEX_TTFB_TIMEOUT_SECONDS": "900", "HERMES_CODEX_EVENT_STALE_TIMEOUT_SECONDS": "900",
             "HERMES_API_CALL_STALE_TIMEOUT": "1800"}


def base_url() -> str:
    return os.environ["FM_LOCAL_BASE_URL"]


class LocalHermes(MemoryHermes):
    async def exec_as_agent(self, environment, command, env=None, **kwargs):
        if env and "OPENAI_BASE_URL" in env:
            env = {**env, "OPENAI_BASE_URL": base_url()}
        return await super().exec_as_agent(environment, command, env={**(env or {}), **WATCHDOGS}, **kwargs)


class LocalHermesLearn(HermesLearn):
    async def install(self, environment) -> None:
        await super().install(environment)
        wrapper = self.logs_dir / "fm_local_driver.py"
        wrapper.parent.mkdir(parents=True, exist_ok=True)
        wrapper.write_text(WRAPPER)
        await environment.upload_file(Path(hermes_dream.__file__), f"{REMOTE}/hermes_dream.py")
        await environment.upload_file(wrapper, f"{REMOTE}/driver.py")

    async def exec_as_agent(self, environment, command, env=None, **kwargs):
        return await super().exec_as_agent(environment, command, env={**(env or {}), "FM_LOCAL_BASE_URL": base_url(), **WATCHDOGS}, **kwargs)
