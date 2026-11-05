#!/usr/bin/env python3
"""Validate official NetworkProbe output and write a count-only egress receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

PROBE_TASK = "dapt-intrusion-detection-workflow-learning"
NETWORK_POLICY = "agent.network_mode=allowlist;agent.allowed_hosts=10.0.2.2"
EXTERNAL_URLS = {
    "https://api.anthropic.com": "vendor",
    "https://api.openai.com": "vendor",
    "https://example.com": "other",
    "https://github.com": "other",
}
NETWORK_HARNESSES = {
    "hermes", "codex", "claude-code", "exposure-none", "exposure-all",
    "delivery-cue", "delivery-scoped", "delivery-categorized",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def task_policy_is_relay_only(path: Path, task: str) -> bool:
    if task != PROBE_TASK:
        return False
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]
        data = tomllib.loads(path.read_text())
    except (OSError, ValueError, ImportError):
        return False
    agent = data.get("agent") or {}
    return (isinstance(agent, dict) and agent.get("network_mode") == "allowlist"
            and agent.get("allowed_hosts") == ["10.0.2.2"])


def manifest_sha256(path: Path, task_config: Path, task: str) -> str | None:
    try:
        manifest = json.loads(path.read_text())
        tasks = manifest.get("tasks")
        if (manifest.get("status") != "pass" or manifest.get("network_policy") != NETWORK_POLICY
                or manifest.get("task_count") != 15 or not isinstance(tasks, dict) or len(tasks) != 15):
            return None
        canonical = json.dumps(tasks, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(canonical).hexdigest()
        if digest != manifest.get("task_copy_sha256"):
            return None
        if tasks.get(task, {}).get("task_toml_sha256") != sha256(task_config):
            return None
        return digest
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def evaluate(raw: dict, *, task: str, harness: str, relay_url: str, raw_sha256: str,
             task_copy_sha256: str, task_config_sha256: str) -> dict:
    parsed = urlparse(relay_url)
    expected = {relay_url, *EXTERNAL_URLS}
    valid_urls = set(raw) == expected
    relay = raw.get(relay_url)
    relay_reachable = isinstance(relay, dict) and relay.get("reachable") is True
    hosts: dict[str, bool] = {"10.0.2.2": relay_reachable}
    vendor_reachable = 0
    other_reachable = 0
    records_valid = True
    for url, kind in EXTERNAL_URLS.items():
        record = raw.get(url)
        if not isinstance(record, dict) or not isinstance(record.get("reachable"), bool):
            records_valid = False
            reachable = False
        else:
            reachable = record["reachable"]
        hosts[urlparse(url).hostname or "unknown"] = reachable
        if reachable and kind == "vendor":
            vendor_reachable += 1
        elif reachable:
            other_reachable += 1

    policy_ok = task == PROBE_TASK
    status = (
        "pass"
        if harness in NETWORK_HARNESSES
        and policy_ok
        and valid_urls
        and records_valid
        and parsed.scheme == "http"
        and parsed.hostname == "10.0.2.2"
        and parsed.path == "/api/version"
        and relay_reachable
        and vendor_reachable == 0
        and other_reachable == 0
        else "fail"
    )
    return {
        "status": status,
        "task": task,
        "harness": harness,
        "network_policy": NETWORK_POLICY,
        "task_copy_sha256": task_copy_sha256,
        "task_config_sha256": task_config_sha256,
        "checked_host_count": len(hosts),
        "checked_hosts": hosts,
        "relay_reachable": relay_reachable,
        "vendor_reachable": vendor_reachable,
        "other_reachable": other_reachable,
        "probe_raw_sha256": raw_sha256,
    }


def write_receipt(path: Path, receipt: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".network-probe-")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(receipt, f, sort_keys=True)
            f.write("\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--raw", type=Path)
    p.add_argument("--receipt", type=Path)
    p.add_argument("--task-config", required=True, type=Path)
    p.add_argument("--task-copy-manifest", required=True, type=Path)
    p.add_argument("--task", required=True)
    p.add_argument("--harness", required=True, choices=sorted(NETWORK_HARNESSES))
    p.add_argument("--relay-url", required=True)
    p.add_argument("--check-task-policy", action="store_true")
    a = p.parse_args()
    copy_digest = manifest_sha256(a.task_copy_manifest, a.task_config, a.task)
    if a.task != PROBE_TASK or not task_policy_is_relay_only(a.task_config, a.task) or copy_digest is None:
        print("NETWORK_PROBE status=fail reason=probe_task_policy_mismatch")
        return 1
    if a.check_task_policy:
        print(f"NETWORK_PROBE_POLICY_OK task={a.task} network_policy={NETWORK_POLICY}")
        return 0
    if a.raw is None or a.receipt is None:
        print("NETWORK_PROBE status=fail reason=probe_arguments_missing")
        return 2
    try:
        raw = json.loads(a.raw.read_text())
        if not isinstance(raw, dict):
            raise ValueError
        digest = sha256(a.raw)
    except (OSError, ValueError, json.JSONDecodeError):
        print("NETWORK_PROBE status=fail reason=probe_output_invalid")
        return 1
    report = evaluate(
        raw,
        task=a.task,
        harness=a.harness,
        relay_url=a.relay_url,
        raw_sha256=digest,
        task_copy_sha256=copy_digest,
        task_config_sha256=sha256(a.task_config),
    )
    write_receipt(a.receipt, report)
    print(
        "NETWORK_PROBE "
        f"status={report['status']} task={a.task} checked_hosts={report['checked_host_count']} "
        f"relay_reachable={int(report['relay_reachable'])} "
        f"vendor_reachable={report['vendor_reachable']} other_reachable={report['other_reachable']} "
        f"raw_sha256={digest}"
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
