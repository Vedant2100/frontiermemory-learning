"""Host-side tests for fm_local.exposure_hermes, on synthetic memory only (never the gated pilot or study memories).

Run: .venv/bin/python -m pytest -q official/tests/test_exposure_hermes.py   (from the repo root)
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "official"))
# The upstream checkout isn't tracked here; a git worktree under .claude/worktrees/ uses the main checkout's copy.
UPSTREAM = next(p for p in (REPO / "frontiermemory", REPO.parents[2] / "frontiermemory") if (p / "src").is_dir())
sys.path.insert(0, str(UPSTREAM / "src"))

from frontier_memory.memory import check_memory  # noqa: E402
from fm_local import exposure_hermes as ex  # noqa: E402


@pytest.fixture
def memory(tmp_path):
    root = tmp_path / "memory"
    (root / "skills" / "alpha").mkdir(parents=True)
    (root / "skills" / "beta" / "references").mkdir(parents=True)
    (root / "MEMORY.md").write_text("- alpha: synthetic skill\n§\n- beta: another\n")
    (root / "skills" / "alpha" / "SKILL.md").write_text("---\nname: alpha\ndescription: synthetic\n---\nStep one.\n")
    (root / "skills" / "beta" / "SKILL.md").write_text("---\nname: beta\ndescription: synthetic\n---\nStep two.\n")
    (root / "skills" / "beta" / "references" / "notes.md").write_text("Reference text ünïcode.\n")
    assert check_memory(root)["ok"]
    return root


def hm_config():
    return {"model": "m", "memory": {"memory_enabled": True, "user_profile_enabled": False}, "agent": {"reasoning_effort": "max"}}


def test_option_is_required_and_closed():
    with pytest.raises(Exception):
        ex.ExposureHermesOptions.model_validate({})
    with pytest.raises(Exception):
        ex.ExposureHermesOptions.model_validate({"exposure": "codex"})
    assert ex.ExposureHermesOptions.model_validate({"exposure": "none"}).exposure == "none"


def test_none_turns_off_block_and_index_only(memory):
    base = hm_config()
    cfg = ex.apply_exposure(base, "none", memory)
    assert cfg["memory"] == {"memory_enabled": False, "user_profile_enabled": False}
    assert "system_prompt" not in cfg["agent"] and cfg["agent"]["reasoning_effort"] == "max"
    assert base["memory"]["memory_enabled"] is True  # input not mutated
    assert ex.skip_upload("none", ex.SKILLS_TARGET) and ex.skip_upload("none", ex.SKILLS_TARGET + "/")
    assert not ex.skip_upload("none", f"{ex.ACTOR_HOME}/memories")  # the whole memory, skills included, stays on disk
    assert not ex.skip_upload("all", ex.SKILLS_TARGET)


def test_all_injects_every_file_in_order_and_keeps_hm_loading(memory):
    cfg = ex.apply_exposure(hm_config(), "all", memory)
    assert cfg["memory"]["memory_enabled"] is True  # HM's block stays
    text = cfg["agent"]["system_prompt"]
    rels = [p.relative_to(memory).as_posix() for p in ex.memory_files(memory)]
    assert rels == sorted(rels) and len(rels) == 4
    positions = [text.index(f"===== memory file: {r} =====") for r in rels]
    assert positions == sorted(positions)
    for p in ex.memory_files(memory):  # every file's full text, byte for byte
        assert p.read_text(encoding="utf-8") in text
    assert ex.injected_text(memory) == text  # deterministic
    with pytest.raises(ValueError):
        ex.apply_exposure({**hm_config(), "agent": {"system_prompt": "x"}}, "all", memory)
    with pytest.raises(ValueError):
        ex.apply_exposure(hm_config(), "codex", memory)


def test_report_holds_counts_and_digest_only(memory):
    sha = check_memory(memory)["memory_sha256"]
    for arm in ("none", "all"):
        r = ex.report(arm, memory, sha)
        blob = json.dumps(r)
        for secret in ("synthetic", "Step one", "alpha", "beta", "notes.md", "Reference"):
            assert secret not in blob
        assert r["memory_sha256"] == sha and r["memory_files"] == 4 and r["skill_files"] == 2
    assert ex.report("none", memory, sha)["injected_bytes"] == 0
    a = ex.report("all", memory, sha)
    assert a["injected_bytes"] == len(ex.injected_text(memory).encode()) and a["injected_tokens_estimate"] == a["injected_bytes"] // 4


def test_upload_filter_restores_environment(memory):
    calls = []

    class Env:
        async def upload_dir(self, source, target):
            calls.append(target)

    env = Env()
    original = env.upload_dir

    async def drive(exposure):
        upload = env.upload_dir

        async def filtered(source, target, *a, **k):
            if ex.skip_upload(exposure, str(target)):
                return None
            return await upload(source, target, *a, **k)

        env.upload_dir = filtered
        try:
            await env.upload_dir(memory, f"{ex.ACTOR_HOME}/memories")
            await env.upload_dir(memory / "skills", ex.SKILLS_TARGET)
        finally:
            del env.upload_dir

    asyncio.run(drive("none"))
    assert calls == [f"{ex.ACTOR_HOME}/memories"]
    assert env.upload_dir.__func__ is original.__func__
    calls.clear(); asyncio.run(drive("all"))
    assert calls == [f"{ex.ACTOR_HOME}/memories", ex.SKILLS_TARGET]


def test_agent_wiring(memory, tmp_path):
    for arm in ("none", "all"):
        agent = ex.ExposureHermes(logs_dir=tmp_path / arm, model_name="openai/qwen3.8:27b-mtp-q4_K_M",
                                  memory_dir=str(memory), exposure=arm, reasoning_effort="max")
        cfg = yaml.safe_load(agent._actor_config("qwen3.8:27b-mtp-q4_K_M"))
        assert cfg["memory"]["memory_enabled"] is (arm == "all")
        assert ("system_prompt" in cfg.get("agent", {})) is (arm == "all")
        assert cfg["agent"]["reasoning_effort"] == "max"
    with pytest.raises(Exception):
        ex.ExposureHermes(logs_dir=tmp_path / "x", model_name="openai/qwen3.8:27b-mtp-q4_K_M", memory_dir=str(memory))
    with pytest.raises(Exception):
        ex.ExposureHermes(logs_dir=tmp_path / "y", model_name="openai/qwen3.8:27b-mtp-q4_K_M", exposure="none")
