"""Generator arm (results/preregistration-arms.md): the official Hermes /learn generator (LocalHermesLearn) with one change,
a longer learn request. Delivery stays HM. The added rules are fixed from published guidance before any run; none was
tuned on task results:

  1. Descriptions say what the skill does and when to use it, with specific key terms: Anthropic, "Skill authoring best
     practices" (platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices): the description "should include
     both what the Skill does and when to use it". The FrontierMemory v1 blog shows a skill with a generic description that
     was "never loaded".
  2. Keep each distinct user preference, environment fact and failure mode as its own specific item, rather than summarising
     them away: ACE (Zhang et al., ICLR 2026, arXiv 2510.04618), itemized incremental updates against "brevity bias".
  3. A few focused skills rather than one exhaustive one: SkillsBench (Li et al., arXiv 2602.12670), focused skills with
     2-3 modules beat larger bundles.

Load through the official hook: frontier-memory generate-memory --harness fm_local.generator_hermes:GeneratorHermesLearn
The driver records the request it used in hermes-result.json ("request"); arm_check.py checks it ends with the added rules.
"""

from __future__ import annotations

from frontier_memory import hermes_dream
from frontier_memory.agents.hermes import REMOTE

from fm_local.arm_logic import GENERATOR_ADDED_RULES as ADDED_RULES
from fm_local.hermes_local import WRAPPER, LocalHermesLearn

REQUEST = hermes_dream.LEARN_REQUEST + ADDED_RULES
GENERATOR_WRAPPER = WRAPPER.replace(
    "hermes_dream.provider_route = provider_route\n",
    "hermes_dream.provider_route = provider_route\nhermes_dream.LEARN_REQUEST = " + repr(REQUEST) + "\n",
)
assert GENERATOR_WRAPPER.count("hermes_dream.LEARN_REQUEST = ") == 1


class GeneratorHermesLearn(LocalHermesLearn):
    @staticmethod
    def name() -> str:
        return "frontier-memory-hermes-learn-generator"

    async def install(self, environment) -> None:
        await super().install(environment)  # official runtime, hermes_dream.py and the local wrapper
        wrapper = self.logs_dir / "fm_generator_driver.py"
        wrapper.write_text(GENERATOR_WRAPPER)
        await environment.upload_file(wrapper, f"{REMOTE}/driver.py")  # replaces the local wrapper with this one

