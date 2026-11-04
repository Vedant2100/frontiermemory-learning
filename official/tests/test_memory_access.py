"""Tests for scripts/memory_access.py on synthetic trial dirs built to the formats in pinned Hermes d923a5eb and MemoryHermes.

Run: .venv/bin/python -m pytest -q official/tests/test_memory_access.py   (from the repo root)
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
import memory_access as ma  # noqa: E402

FILES = ["MEMORY.md", "skills/data/alpha/SKILL.md", "skills/data/alpha/references/notes.md", "skills/beta/SKILL.md"]


def call(tool, /, **args):
    return {"id": "x", "type": "function", "function": {"name": tool, "arguments": json.dumps(args)}}


def make_trial(root: Path, name: str, turns: list[list[dict]], exposure=None, memory=True, fmt="session"):
    t = root / name
    (t / "agent").mkdir(parents=True)
    meta = {"frontier_memory": {"sha256": "abc", "total_bytes": 10, "files": FILES} if memory else None}
    if exposure:
        meta["fm_exposure"] = {"exposure": exposure}
    (t / "result.json").write_text(json.dumps({"task_name": "letta-ai/t", "agent_result": {"metadata": meta},
                                               "verifier_result": {"rewards": {"reward": 0.0}}}))
    if fmt == "session":
        msgs = [{"role": "user", "content": "task"}]
        for calls in turns:
            msgs += [{"role": "assistant", "content": "", "tool_calls": calls}, {"role": "tool", "content": "out"}]
        (t / "agent" / "hermes-session.jsonl").write_text(json.dumps({"id": "s", "messages": msgs}) + "\n")
    else:
        steps = [{"source": "user", "message": "task"}] + [
            {"source": "agent", "tool_calls": [{"function_name": c["function"]["name"], "arguments": json.loads(c["function"]["arguments"])} for c in calls]}
            for calls in turns]
        (t / "agent" / "trajectory.json").write_text(json.dumps({"steps": steps}))
    return t


def test_opens_kinds_and_first_turn(tmp_path):
    t = make_trial(tmp_path, "a__1", [
        [call("terminal", command="ls /workspace"), call("terminal", command="ls /tmp/hermes/memories")],   # turn 0: listed only
        [call("skill_view", name="plan")],                                                                  # turn 1: bundled skill
        [call("read_file", path="/tmp/hermes/memories/MEMORY.md")],                                          # turn 2: first open
        [call("skill_view", name="alpha"), call("skill_view", name="data/alpha", file_path="references/notes.md")],
        [call("terminal", command="grep -rn token /tmp/hermes/skills/beta"), call("execute_code", code="open('/tmp/hermes/skills/beta/SKILL.md').read()")],
        [call("terminal", command="cat /tmp/hermes/skills/plan/SKILL.md")],                                  # bundled skill dir: not memory
    ])
    r = ma.measure(t, None)
    assert r["tool_calls"] == 9 and r["opened"] and r["opens"] == 5
    assert r["first_open_turn"] == 2 and r["tool_calls_before_first_open"] == 3
    assert r["open_kinds"] == {"MEMORY.md": 1, "SKILL.md": 2, "other": 1, "search": 1}
    assert r["listed_only_calls"] == 1 and r["bundled_skill_views"] == 1
    assert r["opened_paths"] == ["MEMORY.md", "skills/beta", "skills/beta/SKILL.md", "skills/data/alpha/SKILL.md", "skills/data/alpha/references/notes.md"]
    assert r["memory_sha256"] == "abc" and r["exposure"] is None and r["has_memory"]


def test_no_open_and_formats_agree(tmp_path):
    turns = [[call("terminal", command="python -m pytest -q")], [call("read_file", path="/workspace/solution.py")]]
    a = ma.measure(make_trial(tmp_path, "b__1", turns, exposure="none"), None)
    b = ma.measure(make_trial(tmp_path, "c__1", turns, exposure="none", fmt="atif"), None)
    for r in (a, b):
        assert not r["opened"] and r["first_open_turn"] is None and r["tool_calls_before_first_open"] is None and r["tool_calls"] == 2
        assert r["exposure"] == "none"
    turns = [[call("terminal", command="cat /tmp/hermes/memories/MEMORY.md")]]
    a = ma.measure(make_trial(tmp_path, "d__1", turns), None)
    b = ma.measure(make_trial(tmp_path, "e__1", turns, fmt="atif"), None)
    assert a["opened"] and b["opened"] and a["open_kinds"] == b["open_kinds"] == {"MEMORY.md": 1}
    r = ma.measure(make_trial(tmp_path, "i__1", [[call("search_files", pattern="token", path="/tmp/hermes")]]), None)
    assert r["opened"] and r["open_kinds"] == {"search": 1} and r["opened_paths"] == ["."]


def test_no_memory_trial_and_summary(tmp_path):
    c = ma.measure(make_trial(tmp_path, "f__1", [[call("terminal", command="cat /tmp/hermes/memories/MEMORY.md")]], memory=False), None)
    assert c["has_memory"] is False and c["memory_sha256"] is None
    rows = [ma.measure(make_trial(tmp_path, f"g__{i}", [[call("read_file", path="/tmp/hermes/memories/MEMORY.md")]] if i else [[]], exposure="all"), None)
            for i in range(3)]
    s = ma.summarise(rows + [c])
    assert s["all"]["trials"] == 3 and s["all"]["opened"] == 2 and s["all"]["memory_digests"] == ["abc"]
    assert s["no-memory"]["trials"] == 1


def test_output_holds_no_content(tmp_path):
    t = make_trial(tmp_path, "h__1", [[call("read_file", path="/tmp/hermes/memories/MEMORY.md")]])
    (t / "agent" / "hermes.txt").write_text("SECRET-MEMORY-TEXT")
    blob = json.dumps(ma.measure(t, None)) + json.dumps(ma.summarise([ma.measure(t, None)]))
    assert "SECRET" not in blob and "task" not in json.dumps(ma.measure(t, None)["open_kinds"])
