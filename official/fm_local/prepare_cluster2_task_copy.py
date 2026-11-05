#!/usr/bin/env python3
"""Create and verify the disposable cluster2 task copy with relay-only agent egress."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import tomllib
from pathlib import Path

TASKS = tuple("""
apex-brightpath-market-share apex-brightpath-seat-surplus apex-eurogrid-curtailment
automationbench-marketing-content-gap-analysis automationbench-sales-chatgpt-proposal-customization
automationbench-sales-partnership-contract awilix-release-tier-explicit awilix-release-tier-implicit
build-word2vec-pipeline cattrs-compositional-changelog cookie-store-compositional-changelog
customer-delivery-contextual-preferences dapt-intrusion-detection-workflow-learning
enterpriseops-csm-26d1b04a enterpriseops-teams-2725d17f
""".split())
RELAY_HOST = "10.0.2.2"
POLICY = "agent.network_mode=allowlist;agent.allowed_hosts=10.0.2.2"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def set_agent_policy(text: str) -> str:
    """Set only the [agent] phase policy keys, preserving other task settings."""
    section = re.search(r"(?m)^\[agent\]\s*$", text)
    if section is None:
        return (text.rstrip() + "\n\n[agent]\nnetwork_mode = \"allowlist\"\n"
                "allowed_hosts = [\"10.0.2.2\"]\n")
    body_start = section.end()
    next_section = re.search(r"(?m)^\[\[?[^\]]+\]\]?\s*$", text[body_start:])
    body_end = body_start + next_section.start() if next_section else len(text)
    body = text[body_start:body_end]

    for key, value in (("network_mode", '"allowlist"'), ("allowed_hosts", '["10.0.2.2"]')):
        pattern = re.compile(rf"(?m)^[ \t]*{key}\s*=.*$")
        replacement = f"{key} = {value}"
        matches = list(pattern.finditer(body))
        if len(matches) > 1:
            raise ValueError(f"duplicate [agent].{key}")
        if matches:
            body = pattern.sub(replacement, body, count=1)
        else:
            body = body.rstrip() + "\n" + replacement + "\n"
    return text[:body_start] + body + text[body_end:]


def config_record(root: Path) -> dict:
    records = {}
    for task in TASKS:
        path = root / task / "task.toml"
        raw = path.read_bytes()
        cfg = tomllib.loads(raw.decode("utf-8"))
        agent = cfg.get("agent") or {}
        if (agent.get("network_mode") != "allowlist"
                or agent.get("allowed_hosts") != [RELAY_HOST]):
            raise ValueError(f"relay-only agent policy mismatch: {task}")
        files = []
        for item in sorted((root / task).rglob("*"), key=lambda p: p.relative_to(root / task).as_posix()):
            relative = item.relative_to(root / task).as_posix()
            if item.is_symlink():
                digest = sha(os.readlink(item).encode())
                kind = "symlink"
            elif item.is_file():
                digest = sha(item.read_bytes())
                kind = "file"
            else:
                continue
            files.append({"path": relative, "kind": kind, "sha256": digest})
        tree_bytes = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
        records[task] = {"task_toml_sha256": sha(raw), "tree_sha256": sha(tree_bytes)}
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return {"status": "pass", "network_policy": POLICY,
            "task_count": len(records), "tasks": records,
            "task_copy_sha256": sha(canonical)}


def agent_policy_removed(config: dict) -> dict:
    clone = json.loads(json.dumps(config))
    agent = clone.get("agent")
    if isinstance(agent, dict):
        agent.pop("network_mode", None)
        agent.pop("allowed_hosts", None)
        if not agent:
            clone.pop("agent", None)
    return clone


def verify_source_parity(source: Path, output: Path) -> None:
    for task in TASKS:
        source_task, output_task = source / task, output / task
        source_paths = {p.relative_to(source_task).as_posix() for p in source_task.rglob("*")}
        output_paths = {p.relative_to(output_task).as_posix() for p in output_task.rglob("*")}
        if source_paths != output_paths:
            raise ValueError(f"task-copy path set differs from source: {task}")
        for relative in sorted(source_paths):
            original, copied = source_task / relative, output_task / relative
            if original.is_symlink() != copied.is_symlink():
                raise ValueError(f"task-copy file type differs from source: {task}/{relative}")
            if original.is_symlink():
                if os.readlink(original) != os.readlink(copied):
                    raise ValueError(f"task-copy symlink differs from source: {task}/{relative}")
            elif original.is_file() and relative != "task.toml":
                if sha(original.read_bytes()) != sha(copied.read_bytes()):
                    raise ValueError(f"task-copy payload differs from source: {task}/{relative}")
        source_config = tomllib.loads((source_task / "task.toml").read_text(encoding="utf-8"))
        copied_config = tomllib.loads((output_task / "task.toml").read_text(encoding="utf-8"))
        if agent_policy_removed(source_config) != agent_policy_removed(copied_config):
            raise ValueError(f"task-copy changed fields outside the approved [agent] policy: {task}")
        agent = copied_config.get("agent") or {}
        if agent.get("network_mode") != "allowlist" or agent.get("allowed_hosts") != [RELAY_HOST]:
            raise ValueError(f"copied agent policy is not relay-only: {task}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument("--output-root", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--expected-task-copy-sha256")
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()

    source = a.source_root.resolve()
    output = a.output_root.resolve()
    manifest = a.manifest.resolve()
    if source == output or source in output.parents or output in source.parents:
        raise ValueError("source and output roots must be disjoint")
    if output != source.parent / "tasks-fm-cluster2":
        raise ValueError("output root must be the dedicated sibling tasks-fm-cluster2")
    if manifest != source.parent / "tasks-fm-cluster2.manifest.json":
        raise ValueError("manifest must be the dedicated sibling cluster2 manifest")

    if not a.verify:
        if output.exists():
            shutil.rmtree(output)
        output.mkdir(parents=True)
        for task in TASKS:
            task_source = source / task
            if not (task_source / "task.toml").is_file():
                raise FileNotFoundError(task_source / "task.toml")
            shutil.copytree(task_source, output / task, symlinks=True)
            toml_path = output / task / "task.toml"
            staged = set_agent_policy(toml_path.read_text(encoding="utf-8"))
            parsed = tomllib.loads(staged)
            if (parsed.get("agent", {}).get("network_mode") != "allowlist"
                    or parsed.get("agent", {}).get("allowed_hosts") != [RELAY_HOST]):
                raise ValueError(f"staged policy failed parse: {task}")
            toml_path.write_text(staged, encoding="utf-8")

    verify_source_parity(source, output)
    record = config_record(output)
    if a.expected_task_copy_sha256 and record["task_copy_sha256"] != a.expected_task_copy_sha256:
        raise ValueError("task copy differs from the frozen gate/preregistration digest")
    if a.verify:
        existing = json.loads(manifest.read_text(encoding="utf-8"))
        if existing != record:
            raise ValueError("task-copy manifest does not match the staged task TOMLs")
    else:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=manifest.parent, prefix=".cluster2-task-copy-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", closefd=True) as stream:
                json.dump(record, stream, sort_keys=True)
                stream.write("\n")
            Path(name).replace(manifest)
        finally:
            Path(name).unlink(missing_ok=True)
    print(f"CLUSTER2_TASK_COPY_OK tasks={len(TASKS)} network_policy={POLICY} task_copy_sha256={record['task_copy_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
