"""Host-side tests for fm_local.forceopen_hermes, on synthetic memory only (never the gated study memories).

Run: .venv/bin/python -m pytest -q official/tests/test_forceopen_hermes.py   (from the repo root)
"""

import json
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "official"))
UPSTREAM = next(p for p in (REPO / "frontiermemory", REPO.parents[2] / "frontiermemory") if (p / "src").is_dir())
sys.path.insert(0, str(UPSTREAM / "src"))

from fm_local import forceopen_hermes as fo  # noqa: E402


def make_memory(root: Path) -> Path:
    base = root / "skills" / "agent-evals" / "eval-task-families"
    (base / "references").mkdir(parents=True)
    (root / "MEMORY.md").write_text("# Learned Hermes skills\n- [eval-task-families](skills/agent-evals/eval-task-families/SKILL.md)\n")
    (base / "SKILL.md").write_text("---\nname: eval-task-families\ndescription: synthetic\n---\nBody.\n")
    for name in ("paths", "family-analysis-mcp", "family-pcap", "family-office-mcp", "commands"):
        (base / "references" / f"{name}.md").write_text(f"{name} text\n")
    return root


@pytest.fixture
def memory(tmp_path):
    return make_memory(tmp_path / "memory")


def test_task_is_read_from_the_trial_directory():
    assert fo.task_of(Path("/x/jobs/j/dapt-intrusion-detection-workflow-learning__AbC1234/agent")) == "dapt-intrusion-detection-workflow-learning"


def test_run1_selects_only_the_named_files_in_plan_order(memory):
    files = fo.select_files("run1", "dapt-intrusion-detection-workflow-learning", memory)
    assert [p.name for p in files] == ["SKILL.md", "family-pcap.md"]
    teams = fo.select_files("run1", "enterpriseops-teams-2725d17f", memory)
    assert [p.name for p in teams] == ["SKILL.md", "family-office-mcp.md"]
    assert [p.name for p in fo.select_files("run1", "apex-brightpath-seat-surplus", memory)] == ["SKILL.md", "paths.md", "family-analysis-mcp.md"]


def test_run4_plan_injects_every_file(memory):
    files = fo.select_files("run4", "automationbench-marketing-content-gap-analysis", memory)
    assert len(files) == 7


def test_task_outside_the_plan_fails_before_any_model_call(memory):
    with pytest.raises(ValueError):
        fo.select_files("run1", "build-word2vec-pipeline", memory)
    with pytest.raises(ValueError):
        fo.select_files("run4", "enterpriseops-teams-2725d17f", memory)


def test_missing_planned_file_is_an_error(tmp_path):
    root = make_memory(tmp_path / "m")
    (root / "skills/agent-evals/eval-task-families/references/family-pcap.md").unlink()
    with pytest.raises(ValueError):
        fo.select_files("run1", "dapt-intrusion-detection-workflow-learning", root)


def test_injected_text_has_full_files_and_report_has_no_text(memory):
    files = fo.select_files("run1", "enterpriseops-teams-2725d17f", memory)
    text = fo.injected_text(files, memory)
    for p in files:
        assert p.read_text(encoding="utf-8") in text
    r = fo.report("run1", "enterpriseops-teams-2725d17f", files, text, "sha")
    blob = json.dumps(r)
    for secret in ("synthetic", "Body.", "family-office-mcp", "office"):
        assert secret not in blob.replace("enterpriseops-teams", "")
    assert r["files_injected"] == 2 and r["injected_bytes"] == len(text.encode())


def test_config_keeps_hm_settings_and_refuses_to_overwrite():
    cfg = {"memory": {"memory_enabled": True}, "agent": {"reasoning_effort": "max"}}
    out = fo.apply_forceopen(cfg, "TEXT")
    assert out["memory"]["memory_enabled"] is True and out["agent"]["system_prompt"] == "TEXT" and out["agent"]["reasoning_effort"] == "max"
    assert "system_prompt" not in cfg["agent"]
    with pytest.raises(ValueError):
        fo.apply_forceopen({"agent": {"system_prompt": "x"}}, "TEXT")


def test_agent_wiring(memory, tmp_path):
    logs = tmp_path / "enterpriseops-teams-2725d17f__Zq9/agent"
    agent = fo.ForceOpenHermes(logs_dir=logs, model_name="openai/qwen3.8:27b-mtp-q4_K_M", memory_dir=str(memory), plan="run1", reasoning_effort="max")
    cfg = yaml.safe_load(agent._actor_config("qwen3.8:27b-mtp-q4_K_M"))
    assert cfg["memory"]["memory_enabled"] is True
    assert "family-office-mcp.md" in cfg["agent"]["system_prompt"] and "family-pcap.md" not in cfg["agent"]["system_prompt"]
    with pytest.raises(Exception):
        fo.ForceOpenHermes(logs_dir=tmp_path / "build-word2vec-pipeline__a/agent", model_name="openai/qwen3.8:27b-mtp-q4_K_M", memory_dir=str(memory), plan="run1")
    with pytest.raises(Exception):
        fo.ForceOpenHermes(logs_dir=logs, model_name="openai/qwen3.8:27b-mtp-q4_K_M", plan="run1")


def test_truncated_trial_directory_names_still_match(memory):
    assert len(fo.select_files("run4", "automationbench-marketing-conten", memory)) == 7
    assert [p.name for p in fo.select_files("run1", "dapt-intrusion-detection-workflo", memory)] == ["SKILL.md", "family-pcap.md"]
    with pytest.raises(ValueError):
        fo.select_files("run4", "enterpriseops-teams-2725d17f", memory)
