#!/usr/bin/env python3
"""Revalidate and receipt the one Hermes gate whose route checker was too strict."""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "c2-gate-hermes-20261105b"
EXECUTED_COMMIT = "a502e51f957ecf7cedbfe589d9191e476fe7df3e"
TASK_PREFIX_LINES = 59
ROUTE_COUNTS = {"/api/show": 10, "/v1/responses": 245}
MEMORY_TASKS = ("customer-delivery-contextual-preferences", "apex-eurogrid-curtailment")
CONTROL_TASK = "awilix-release-tier-implicit"
MODEL = "22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643"
CORPUS = "19346a3e46b022ed1def552f8e4f4c50030cefd3250a7a8e10676b46b370b763"
TOOLS = "9af28c2f8210779f442aa36a1d73553630441af5"
UPDATE = "8cea454bfe730e111d19dac04dd9649290b0c0b0"
EXPECTED_CHANGED = {
    "official/vm/next-gate-cluster2.sh",
    "scripts/check_gate_cluster2.py",
    "scripts/finalize_gate_posthoc_cluster2.py",
}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def run_checked(argv: list[str]) -> None:
    print("$", " ".join(argv))
    subprocess.run(argv, cwd=ROOT, check=True)


def main() -> int:
    try:
        require(git("branch", "--show-current") == "cluster2", "wrong branch")
        require(not git("status", "--porcelain"), "worktree must be clean before finalization")
        validator_commit = git("rev-parse", "HEAD")
        require(git("merge-base", "--is-ancestor", EXECUTED_COMMIT, validator_commit) == "",
                "validator commit does not descend from the executed task commit")
        changed = set(git("diff", "--name-only", f"{EXECUTED_COMMIT}..{validator_commit}").splitlines())
        require(changed == EXPECTED_CHANGED, f"post-hoc diff is outside the exact allowlist: {sorted(changed)}")
        old_gate = git("show", f"{EXECUTED_COMMIT}:official/vm/next-gate-cluster2.sh")
        new_gate = (ROOT / "official/vm/next-gate-cluster2.sh").read_text()
        require(old_gate.splitlines()[:TASK_PREFIX_LINES] == new_gate.splitlines()[:TASK_PREFIX_LINES],
                "task-launch portion of the executed gate script changed")
        require(git("rev-parse", "origin/main:HANDOFF-updates.md") == UPDATE, "handoff update changed")

        slug = "HERMES"
        failed = ROOT / "official/vm/GATE_FAILED_HERMES_CLUSTER2"
        passed = ROOT / "official/vm/GATE_PASSED_HERMES_CLUSTER2"
        require(failed.is_file() and failed.read_text().strip() == "wrong or missing model route",
                "original route-check failure marker is absent or changed")
        failed_hash = sha(failed)
        gate_id = RUN_ID
        mem_job = f"fm-gate-memory-hermes-{gate_id}"
        ctrl_job = f"fm-gate-control-hermes-{gate_id}"
        base = ROOT / "results/official-cluster2" / gate_id
        result_root = ROOT / "results/official-cluster2"
        receipt = result_root / f"gate-receipt-hermes-{gate_id}.json"
        log = ROOT / "official/logs/cluster2" / f"gate-{gate_id}.log"
        require(log.is_file(), "original gate log is missing")
        raw_log = log.read_bytes()
        require(raw_log.endswith(b"\n"), "original gate log does not end on a line boundary")
        correction_line = ("POSTHOC_GATE_CORRECTION type=ollama_metadata_route_allowlist "
                           f"gate={gate_id} executed_commit={EXECUTED_COMMIT} validator_commit={validator_commit} "
                           "routes=/api/show:10,/v1/responses:245 original_failure=wrong_or_missing_model_route")
        correction_bytes = correction_line.encode() + b"\n"
        if correction_bytes in raw_log:
            require(raw_log.endswith(correction_bytes) and raw_log.count(correction_bytes) == 1,
                    "existing post-hoc correction line is misplaced or duplicated")
            pre_log = raw_log[:-len(correction_bytes)]
        else:
            require(correction_line.encode() not in raw_log, "partial post-hoc correction line already exists")
            pre_log = raw_log
        pre_log_hash = sha_bytes(pre_log)
        final_log_hash = sha_bytes(pre_log + correction_bytes)

        user = os.environ.get("USER")
        require(bool(user), "USER is unset")
        olog = Path(f"/tmp/fm-c2-{user}/ollama-{gate_id}")
        require(olog.is_dir() and (olog / "server.log").is_file() and (olog / "relay.log").is_file(),
                "gate Ollama logs are missing from the expected local /tmp path")
        require(str(olog.resolve()).startswith(f"/tmp/fm-c2-{user}/"), "serving logs are outside the local temp root")
        run_checked([sys.executable, "official/vm/check-serving.py", str(olog), "0", "0",
                     "--need-keepalive", "--summaries", str(base)])

        memory_audit_path = base / f"audit-config-{mem_job}.json"
        control_audit_path = base / f"audit-config-{ctrl_job}.json"
        memory_audit = json.loads(memory_audit_path.read_text())
        control_audit = json.loads(control_audit_path.read_text())
        for audit, kind, count in ((memory_audit, "memory", 2), (control_audit, "control", 1)):
            require(audit.get("status") == "pass" and audit.get("harness") == "hermes"
                    and audit.get("kind") == kind and audit.get("trial_count") == count
                    and audit.get("effort") == "max" and audit.get("concurrency") == 1
                    and audit.get("environment") == "docker" and audit.get("allowed_host_count") == 1
                    and audit.get("timeout_multiplier") == 1 and audit.get("agent_timeout_multiplier") == 1
                    and audit.get("model_unavailable") == 0 and audit.get("errors") == [],
                    f"{kind} configuration audit did not pass the gate protocol")

        mem_summary = base / f"summary-{mem_job}.jsonl"
        ctrl_summary = base / f"summary-{ctrl_job}.jsonl"
        expected_memory = memory_audit.get("memory_sha256")
        require(isinstance(expected_memory, list) and len(expected_memory) == 1,
                "memory audit digest is missing or ambiguous")
        run_checked([sys.executable, "scripts/validate_set_cluster2.py", str(mem_summary), "--kind", "memory",
                     "--tasks", *MEMORY_TASKS, "--attempts", "1", "--expected-memory", expected_memory[0]])
        run_checked([sys.executable, "scripts/validate_set_cluster2.py", str(ctrl_summary), "--kind", "control",
                     "--task", CONTROL_TASK])
        mem_rows = [json.loads(x) for x in mem_summary.read_text().splitlines() if x.strip()]
        control_rows = [json.loads(x) for x in ctrl_summary.read_text().splitlines() if x.strip()]
        require(len(mem_rows) == 2 and len(control_rows) == 1, "gate summary trial counts changed")
        require({r.get("memory_sha256") for r in mem_rows} == {expected_memory[0]},
                "memory task output digests differ from the audit")
        require(all(r.get("valid") is True and r.get("finished") is True and not r.get("model_unavailable")
                    for r in mem_rows + control_rows), "a gate task is invalid, unfinished, or model-unavailable")

        first_round = re.findall(r"round 1: (\d+) trial\(s\) with no reward set aside", raw_log.decode(errors="replace"))
        require(first_round == ["0", "0"], f"expected zero first-round reruns, found {first_round}")
        key_lines = re.findall(r"saved files holding key: (\d+)", raw_log.decode(errors="replace"))
        require(key_lines == ["0", "0"], f"saved-key audit did not report zero leaks: {key_lines}")
        require(raw_log.count(b"AUDIT_OK") == 2, "both task configuration audits did not record AUDIT_OK")

        relay_rows = [json.loads(x) for x in (olog / "relay.log").read_text().splitlines() if x.strip()]
        posts = [r for r in relay_rows if r.get("method") == "POST"]
        routes = dict(collections.Counter(r.get("path") for r in posts))
        require(routes == ROUTE_COUNTS, f"POST route counts differ: {routes}")
        require(len(posts) == sum(ROUTE_COUNTS.values()) and all(r.get("upstream_status") == 200 for r in posts),
                "a POST request did not receive upstream HTTP 200")

        reference_path = result_root / "reference-cluster2.json"
        reference = json.loads(reference_path.read_text())
        require(reference.get("status") == "pass" and reference.get("task_count") == 15,
                "reference receipt is incomplete")
        require(reference.get("model_manifest_sha256") == MODEL
                and reference.get("corpus_manifest_sha256") == CORPUS
                and reference.get("frontiermemory_commit") == TOOLS,
                "reference environment differs from the pinned gate environment")
        require(git("merge-base", "--is-ancestor", reference.get("cluster2_commit", ""), EXECUTED_COMMIT) == "",
                "reference source is not an ancestor of the task-execution commit")
        require(git("rev-parse", "origin/main:HANDOFF-updates.md") == UPDATE, "handoff changed during validation")

        audits = {mem_job: memory_audit, ctrl_job: control_audit}
        record = {
            "status": "pass",
            "gate_job": gate_id,
            "harness": "hermes",
            "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "cluster2_commit": validator_commit,
            "task_execution_commit": EXECUTED_COMMIT,
            "handoff_blob": UPDATE,
            "model": "qwen3.8:27b-mtp-q4_K_M",
            "model_manifest_sha256": MODEL,
            "corpus_manifest_sha256": CORPUS,
            "reference_receipt_sha256": sha(reference_path),
            "task_release": "letta-ai/frontier-memory@v1.0",
            "frontiermemory_commit": TOOLS,
            "task_manifest_sha256": reference["task_manifest_sha256"],
            "harbor_version": reference["harbor_version"],
            "docker_server_version": reference["docker_server_version"],
            "summaries": {mem_job: sha(mem_summary), ctrl_job: sha(ctrl_summary)},
            "config_audits": {job: sha(base / f"audit-config-{job}.json") for job in audits},
            "network_probe_receipts": {},
            "memory_sha256": expected_memory,
            "memory_trials": len(mem_rows),
            "control_trials": len(control_rows),
            "model_post_routes": routes,
            "serving_log_sha256": {"server": sha(olog / "server.log"), "relay": sha(olog / "relay.log")},
            "gate_log_sha256": final_log_hash,
            "judge": "anthropic/claude-opus-5-5",
            "settings": {
                "model_context_tokens": 262144,
                "effort": {job: audits[job]["effort"] for job in audits},
                "concurrency": {job: audits[job]["concurrency"] for job in audits},
                "environment": {job: audits[job]["environment"] for job in audits},
                "allowed_host_count": {job: audits[job]["allowed_host_count"] for job in audits},
                "timeout_multiplier": {job: audits[job]["timeout_multiplier"] for job in audits},
                "agent_timeout_multiplier": {job: audits[job]["agent_timeout_multiplier"] for job in audits},
            },
            "posthoc_correction": {
                "executed_commit": EXECUTED_COMMIT,
                "validator_commit": validator_commit,
                "changed_files": sorted(EXPECTED_CHANGED),
                "task_prefix_lines_unchanged": TASK_PREFIX_LINES,
                "failed_marker_sha256": failed_hash,
                "pre_correction_log_sha256": pre_log_hash,
                "correction_line": correction_line,
                "route_counts": routes,
            },
        }
        if receipt.exists():
            existing_record = json.loads(receipt.read_text())
            comparable_existing = dict(existing_record)
            comparable_expected = dict(record)
            comparable_existing.pop("created_utc", None)
            comparable_expected.pop("created_utc", None)
            require(comparable_existing == comparable_expected,
                    "existing partial receipt differs from revalidated gate evidence")
        else:
            fd, name = tempfile.mkstemp(dir=result_root, prefix=".gate-receipt-")
            with os.fdopen(fd, "w") as stream:
                json.dump(record, stream, sort_keys=True)
                stream.write("\n")
            os.chmod(name, 0o600)
            os.replace(name, receipt)

        if not raw_log.endswith(correction_bytes):
            with log.open("ab") as stream:
                stream.write(correction_bytes)
        require(sha(log) == final_log_hash, "gate log differs from the expected post-hoc correction")
        marker_body = f"results/official-cluster2/{receipt.name} {sha(receipt)}\n"
        if passed.exists():
            require(passed.read_text() == marker_body, "existing passed marker differs from the post-hoc receipt")
        else:
            fd, name = tempfile.mkstemp(dir=passed.parent, prefix=".gate-passed-")
            with os.fdopen(fd, "w") as stream:
                stream.write(marker_body)
            os.chmod(name, 0o600)
            os.replace(name, passed)

        try:
            run_checked([sys.executable, "scripts/check_gate_cluster2.py", "--harness", "hermes"])
        except subprocess.CalledProcessError:
            passed.unlink(missing_ok=True)
            raise
        print(f"POSTHOC_GATE_FINALIZED gate={gate_id} receipt_sha256={sha(receipt)}")
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"POSTHOC_FINALIZATION_FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
