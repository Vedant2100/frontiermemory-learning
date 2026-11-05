import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "fm_local" / "exposure_measure.py"


def make(tmp, prompt):
    mem = tmp / "gen" / "t1" / "artifacts" / "memory"
    (mem / "skills" / "release-tier-checklist").mkdir(parents=True)
    (mem / "MEMORY.md").write_text("# Index\nAlways read the release notes before tagging a tier.\n")
    (mem / "skills" / "release-tier-checklist" / "SKILL.md").write_text("Run the full test suite before publishing anything.\n")
    trial = tmp / "job" / "task__abc"
    (trial / "agent").mkdir(parents=True)
    (trial / "result.json").write_text("{}")
    (trial / "agent" / "hermes-session.jsonl").write_text(json.dumps({"system_prompt": prompt}) + "\n")
    return tmp / "job", tmp / "gen"


def run(job, gen, arm):
    return subprocess.run([sys.executable, str(SCRIPT), str(job), str(gen), arm], capture_output=True, text=True)


def test_none_passes_without_memory_and_fails_with_it(tmp_path):
    job, gen = make(tmp_path, "You are a helpful agent.")
    assert run(job, gen, "none").returncode == 0
    job, gen = make(tmp_path / "b", "Always read the release notes before tagging a tier. skills: release-tier-checklist")
    assert run(job, gen, "none").returncode == 1


def test_hm_needs_memory_md_and_all_needs_every_file(tmp_path):
    job, gen = make(tmp_path, "Always read the release notes before tagging a tier.")
    assert run(job, gen, "hm").returncode == 0
    assert run(job, gen, "all").returncode == 1
    job, gen = make(tmp_path / "b", "Always read the release notes before tagging a tier.\nRun the full test suite before publishing anything.")
    assert run(job, gen, "all").returncode == 0


def test_output_has_counts_not_text(tmp_path):
    job, gen = make(tmp_path, "Always read the release notes before tagging a tier.")
    out = run(job, gen, "hm").stdout
    assert "release notes" not in out and "files shown 1 of 2" in out
