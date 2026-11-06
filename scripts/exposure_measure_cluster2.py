#!/usr/bin/env python3
"""Count memory probes present in saved task-agent logs; never print memory text."""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path
from typing import Any


def memory_probes(root: Path) -> tuple[dict[str, str], set[str]]:
    probes: dict[str, str] = {}
    skills: set[str] = set()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        best = max((line.strip() for line in lines), key=len, default="")[:80]
        if len(best) >= 20:
            probes[path.relative_to(root).as_posix()] = best
        if path.name == "SKILL.md":
            skills.add(path.parent.name)
    return probes, skills


def strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def conversation_strings(messages: Any):
    if not isinstance(messages, list):
        return
    for message in messages:
        if isinstance(message, dict) and (message.get("role") == "system" or message.get("type") == "system"):
            continue
        yield from strings(message)


def read_json_records(path: Path):
    try:
        raw = path.read_text(errors="replace")
    except OSError:
        return
    if path.suffix == ".jsonl":
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
    else:
        try:
            yield json.loads(raw)
        except json.JSONDecodeError:
            return


def log_text(trial: Path, harness: str) -> tuple[str | None, str, str]:
    agent = trial / "agent"
    if harness.startswith("exposure-") or harness.startswith("delivery-") or harness == "hermes":
        session = agent / "hermes-session.jsonl"
        records = list(read_json_records(session)) if session.is_file() else []
        if not records:
            return None, "", "missing"
        prompt = records[0].get("system_prompt") if isinstance(records[0], dict) else None
        message_text = "\n".join(
            text
            for record in records
            if isinstance(record, dict)
            for text in conversation_strings(record.get("messages") or [])
        )
        return prompt if isinstance(prompt, str) else None, message_text, "captured" if isinstance(prompt, str) else "missing"

    paths = []
    if harness == "codex":
        paths.extend([agent / "trajectory.json"])
    elif harness == "claude-code":
        paths.extend(agent.rglob("*.jsonl"))
        paths.extend(agent.rglob("trajectory.json"))
    else:
        return None, "", "unsupported"
    texts: list[str] = []
    seen: set[Path] = set()
    for path in paths:
        if path in seen or not path.is_file() or path.stat().st_size > 32 * 1024 * 1024:
            continue
        seen.add(path)
        for record in read_json_records(path):
            texts.extend(strings(record))
    return None, "\n".join(texts), "not_captured" if texts else "missing"


def count_hits(probes: dict[str, str], skills: set[str], text: str) -> tuple[int, int, bool]:
    files = sum(probe in text for probe in probes.values())
    indexed = sum(name in text for name in skills)
    return files, indexed, any("MEMORY.md" == name and probe in text for name, probe in probes.items())


def measure(trial: Path, probes: dict[str, str], skills: set[str], harness: str, arm: str) -> dict:
    prompt, transcript, capture = log_text(trial, harness)
    result = json.loads((trial / "result.json").read_text())
    metadata = ((result.get("agent_result") or {}).get("metadata") or {})
    frontier_memory = metadata.get("frontier_memory") or {}
    startup_files, startup_skills, memory_md = count_hits(probes, skills, prompt or "")
    # conversation_strings excludes system-role messages, so every match here came from
    # a later logged request/message, including delivery tool-result insertions.
    later_files, later_skills, _ = count_hits(probes, skills, transcript)
    row = {
        "trial": trial.name,
        "task": result.get("task_name"),
        "memory_sha256": frontier_memory.get("sha256"),
        "harness": harness,
        "arm": arm,
        "startup_prompt_capture": capture,
        "eligible_memory_file_probes": len(probes),
        "memory_skill_names": len(skills),
        "startup_files_shown": startup_files,
        "startup_skills_indexed": startup_skills,
        "startup_memory_md_shown": memory_md,
        "later_files_seen": later_files,
        "later_skills_seen": later_skills,
    }
    if capture == "missing":
        return {**row, "ok": False}
    if harness.startswith("exposure-"):
        if arm == "none":
            ok = startup_files == 0 and startup_skills == 0
        elif arm == "all":
            ok = startup_files == len(probes)
        else:
            ok = False
    elif arm == "hm" and capture == "captured":
        ok = memory_md
    else:
        # Codex and Claude Code transcript exports omit a directly captured startup prompt.
        # Their own session logs are still scanned for actual memory text.
        ok = True
    return {**row, "ok": bool(ok)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_job", type=Path)
    parser.add_argument("memory_dir", type=Path)
    parser.add_argument("--harness", required=True, choices=("hermes", "codex", "claude-code", "exposure-none", "exposure-all",
                                                               "delivery-cue", "delivery-scoped", "delivery-categorized"))
    parser.add_argument("--arm", required=True, choices=("none", "hm", "all", "cue", "scoped", "categorized"))
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    probes, skills = memory_probes(args.memory_dir)
    trials = sorted(p for p in args.task_job.iterdir() if p.is_dir() and (p / "result.json").is_file())
    if not trials:
        print("EXPOSURE_MEASURE_FAILED trials=0", file=sys.stderr)
        return 1
    if args.expected_count is not None and len(trials) != args.expected_count:
        print(f"EXPOSURE_MEASURE_FAILED expected={args.expected_count} actual={len(trials)}", file=sys.stderr)
        return 1
    rows = [measure(t, probes, skills, args.harness, args.arm) for t in trials]
    args.out.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    summary = {
        "harness": args.harness,
        "arm": args.arm,
        "trials": len(rows),
        "eligible_memory_file_probes": len(probes),
        "memory_skill_names": len(skills),
        "startup_prompt_capture": rows[0]["startup_prompt_capture"],
        "startup_files_shown_total": sum(row["startup_files_shown"] for row in rows),
        "startup_skills_indexed_total": sum(row["startup_skills_indexed"] for row in rows),
        "later_files_seen_total": sum(row["later_files_seen"] for row in rows),
        "later_skills_seen_total": sum(row["later_skills_seen"] for row in rows),
        "ok_trials": sum(row["ok"] for row in rows),
    }
    args.out.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("EXPOSURE_MEASURE " + json.dumps(summary, sort_keys=True), file=sys.stderr)
    return 0 if summary["ok_trials"] == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
