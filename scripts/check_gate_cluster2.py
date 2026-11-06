"""Verify count-only receipts for each cluster2 task-agent harness gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = "22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643"
CORPUS = "19346a3e46b022ed1def552f8e4f4c50030cefd3250a7a8e10676b46b370b763"
TOOLS = "9af28c2f8210779f442aa36a1d73553630441af5"
UPDATE = "1f8025c520ff5a51861854da05bd53a1645c6f91"
HARNESSES = ("hermes", "codex", "claude-code")
MEMORY_TASKS = ("customer-delivery-contextual-preferences", "apex-eurogrid-curtailment")
CONTROL_TASK = "awilix-release-tier-implicit"
ROUTE = {"hermes": "/v1/responses", "codex": "/v1/responses", "claude-code": "/v1/messages"}
POSTHOC_VALIDATOR_FILES = {
    "official/vm/next-gate-cluster2.sh",
    "scripts/check_gate_cluster2.py",
    "scripts/finalize_gate_posthoc_cluster2.py",
}
POST_TASK_PREFIX_LINES = 59
POSTHOC_GATE_ID = "c2-gate-hermes-20261105b"
POSTHOC_EXECUTED_COMMIT = "a502e51f957ecf7cedbfe589d9191e476fe7df3e"
NETWORK_PROBE_TASK = "dapt-intrusion-detection-workflow-learning"
STUDY_TASKS = frozenset("""
apex-brightpath-market-share apex-brightpath-seat-surplus apex-eurogrid-curtailment
automationbench-marketing-content-gap-analysis automationbench-sales-chatgpt-proposal-customization
automationbench-sales-partnership-contract awilix-release-tier-explicit awilix-release-tier-implicit
build-word2vec-pipeline cattrs-compositional-changelog cookie-store-compositional-changelog
customer-delivery-contextual-preferences dapt-intrusion-detection-workflow-learning
enterpriseops-csm-26d1b04a enterpriseops-teams-2725d17f
""".split())
NETWORK_PROBE_HOSTS = {
    "10.0.2.2": True,
    "api.anthropic.com": False,
    "api.openai.com": False,
    "example.com": False,
    "github.com": False,
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def check_one(harness: str, require_prereg: bool) -> str:
    slug = harness.upper().replace("-", "_")
    marker = ROOT / f"official/vm/GATE_PASSED_{slug}_CLUSTER2"
    bits = marker.read_text().split()
    require(len(bits) == 2, f"{harness}: gate marker malformed")
    rel, wanted_sha = bits
    require(rel.startswith(f"results/official-cluster2/gate-receipt-{harness}-")
            and re.fullmatch(r"[0-9a-f]{64}", wanted_sha), f"{harness}: marker path or digest malformed")
    receipt_path = (ROOT / rel).resolve()
    require(receipt_path.is_relative_to(ROOT) and receipt_path.is_file(), f"{harness}: receipt missing or outside clone")
    require(digest(receipt_path) == wanted_sha, f"{harness}: receipt digest mismatch")
    receipt = json.loads(receipt_path.read_text())
    effort_receipt = ROOT / "results/effort-check-cluster2.json"
    require(effort_receipt.is_file() and digest(effort_receipt) == receipt.get("effort_check_sha256"),
            f"{harness}: U5 effort-check receipt missing or changed")
    subprocess.run([sys.executable, str(ROOT / "scripts/validate_effort_check_cluster2.py"), str(effort_receipt)],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    gate_id = receipt.get("gate_job")
    require(isinstance(gate_id, str) and re.fullmatch(r"c2-[A-Za-z0-9_-]+", gate_id), f"{harness}: gate id malformed")
    gate_commit = receipt.get("cluster2_commit")
    require(isinstance(gate_commit, str) and git("merge-base", "--is-ancestor", gate_commit, "HEAD") == "",
            f"{harness}: gate commit is not an ancestor")
    require(receipt.get("status") == "pass" and receipt.get("harness") == harness, f"{harness}: receipt identity/status differs")
    require(receipt.get("handoff_blob") == UPDATE, f"{harness}: used another handoff revision")
    require(receipt.get("model_manifest_sha256") == MODEL and receipt.get("corpus_manifest_sha256") == CORPUS,
            f"{harness}: model or corpus digest differs")
    require(receipt.get("task_release") == "letta-ai/frontier-memory@v1.0" and receipt.get("frontiermemory_commit") == TOOLS,
            f"{harness}: official task/tool pin differs")
    require(receipt.get("judge") == "anthropic/claude-opus-5-5", f"{harness}: judge differs")
    route = ROUTE[harness]
    routes = receipt.get("model_post_routes")
    require(isinstance(routes, dict) and routes.get(route, 0) > 0
            and set(routes) <= {route, "/v1/responses", "/api/show"},
            f"{harness}: model route missing or unexpected")

    reference = ROOT / "results/official-cluster2/reference-cluster2.json"
    require(digest(reference) == receipt.get("reference_receipt_sha256"), f"{harness}: reference receipt changed")
    ref = json.loads(reference.read_text())
    require(ref.get("status") == "pass" and ref.get("task_count") == 15, f"{harness}: reference check is incomplete")
    require(git("merge-base", "--is-ancestor", ref.get("cluster2_commit", ""), gate_commit) == "",
            f"{harness}: reference source is not an ancestor of gate code")
    require(ref.get("model_manifest_sha256") == MODEL and ref.get("corpus_manifest_sha256") == CORPUS
            and ref.get("frontiermemory_commit") == TOOLS, f"{harness}: reference environment differs")
    require(receipt.get("task_manifest_sha256") == ref.get("task_manifest_sha256")
            and receipt.get("harbor_version") == ref.get("harbor_version")
            and receipt.get("docker_server_version") == ref.get("docker_server_version"),
            f"{harness}: task or Docker environment differs from reference check")

    summaries = receipt.get("summaries")
    mem_job, ctrl_job = f"fm-gate-memory-{harness}-{gate_id}", f"fm-gate-control-{harness}-{gate_id}"
    require(isinstance(summaries, dict) and set(summaries) == {mem_job, ctrl_job}, f"{harness}: summary set malformed")
    memory_access_receipts = receipt.get("memory_access_receipts")
    require(isinstance(memory_access_receipts, dict) and set(memory_access_receipts) == {mem_job, ctrl_job},
            f"{harness}: memory-access receipt set malformed")
    network_probe_receipts = receipt.get("network_probe_receipts") or {}
    require(isinstance(network_probe_receipts, dict)
            and set(network_probe_receipts) == {mem_job, ctrl_job},
            f"{harness}: egress-probe receipt set malformed")
    expected_network_policy = "agent.network_mode=allowlist;agent.allowed_hosts=10.0.2.2"
    task_copy_digest = receipt.get("task_copy_sha256")
    task_copy_manifest_digest = receipt.get("task_copy_manifest_sha256")
    require(receipt.get("network_policy") == expected_network_policy
            and isinstance(task_copy_digest, str) and re.fullmatch(r"[0-9a-f]{64}", task_copy_digest)
            and isinstance(task_copy_manifest_digest, str) and re.fullmatch(r"[0-9a-f]{64}", task_copy_manifest_digest),
            f"{harness}: relay-only task-copy receipt metadata malformed")
    mem_digest = receipt.get("memory_sha256")
    require(isinstance(mem_digest, list) and len(mem_digest) == 1 and isinstance(mem_digest[0], str)
            and re.fullmatch(r"[0-9a-f]{64}", mem_digest[0]), f"{harness}: memory digest absent or inconsistent")
    base = ROOT / "results/official-cluster2" / gate_id
    for job, kind, tasks in ((mem_job, "memory", MEMORY_TASKS), (ctrl_job, "control", (CONTROL_TASK,))):
        summary = base / f"summary-{job}.jsonl"
        access_path = base / f"memory-access-{job}.jsonl"
        access_check_path = base / f"memory-access-check-{job}.json"
        require(summary.is_file() and digest(summary) == summaries[job], f"{harness}: {job} summary missing/changed")
        access_hashes = memory_access_receipts[job]
        require(isinstance(access_hashes, dict)
                and access_path.is_file() and digest(access_path) == access_hashes.get("report_sha256")
                and access_check_path.is_file() and digest(access_check_path) == access_hashes.get("check_sha256"),
                f"{harness}: {job} memory-access evidence missing/changed")
        access_check = json.loads(access_check_path.read_text())
        expected_digest = mem_digest[0] if kind == "memory" else None
        require(access_check.get("status") == "pass" and access_check.get("harness") == harness
                and access_check.get("kind") == kind and access_check.get("trial_count") == (2 if kind == "memory" else 1)
                and access_check.get("summary_sha256") == digest(summary)
                and access_check.get("memory_access_sha256") == digest(access_path)
                and access_check.get("memory_sha256") == expected_digest,
                f"{harness}: {job} memory-access evidence does not match its inputs")
        subprocess.run([sys.executable, str(ROOT / "scripts/validate_memory_access_cluster2.py"),
                        str(summary), str(access_path), "--harness", harness, "--kind", kind,
                        "--receipt", str(access_check_path), "--verify-receipt"],
                       cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        cmd = [sys.executable, str(ROOT / "scripts/validate_set_cluster2.py"), str(summary), "--kind", kind,
               "--tasks", *tasks, "--attempts", "1"]
        if kind == "memory":
            cmd += ["--expected-memory", mem_digest[0]]
        subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    require(receipt.get("memory_trials") == 2 and receipt.get("control_trials") == 1, f"{harness}: gate trial count differs")
    config_audits = receipt.get("config_audits")
    require(isinstance(config_audits, dict) and set(config_audits) == {mem_job, ctrl_job},
            f"{harness}: configuration audit hashes are missing")
    settings = receipt.get("settings") or {}
    require(settings.get("model_context_tokens") == 262144, f"{harness}: model context differs")
    for job, kind, trials in ((mem_job, "memory", 2), (ctrl_job, "control", 1)):
        audit_path = base / f"audit-config-{job}.json"
        require(audit_path.is_file() and digest(audit_path) == config_audits[job],
                f"{harness}: {job} configuration audit missing/changed")
        audit = json.loads(audit_path.read_text())
        require(audit.get("status") == "pass" and audit.get("harness") == harness and audit.get("kind") == kind,
                f"{harness}: {job} configuration audit failed")
        task_copy_manifest = base / f"task-copy-manifest-{job}.json"
        require(task_copy_manifest.is_file() and digest(task_copy_manifest) == audit.get("task_copy_manifest_sha256")
                == task_copy_manifest_digest,
                f"{harness}: {job} task-copy manifest missing/changed")
        manifest = json.loads(task_copy_manifest.read_text())
        manifest_tasks = manifest.get("tasks")
        manifest_digest = hashlib.sha256(json.dumps(manifest_tasks, sort_keys=True, separators=(",", ":")).encode()).hexdigest() if isinstance(manifest_tasks, dict) else None
        require(audit.get("network_policy") == expected_network_policy
                and audit.get("task_copy_sha256") == task_copy_digest
                and manifest.get("network_policy") == expected_network_policy
                and manifest.get("task_count") == len(STUDY_TASKS)
                and isinstance(manifest_tasks, dict) and set(manifest_tasks) == STUDY_TASKS
                and manifest.get("task_copy_sha256") == task_copy_digest == manifest_digest,
                f"{harness}: {job} audit does not bind the approved task-copy policy")
        require(audit.get("trial_count") == trials and audit.get("effort") == "max"
                and audit.get("concurrency") == 1 and audit.get("environment") == "docker"
                and audit.get("allowed_host_count") == 1 and audit.get("timeout_multiplier") == 1
                and audit.get("agent_timeout_multiplier") == 1 and audit.get("model_unavailable") == 0,
                f"{harness}: {job} observed settings differ from the gate protocol")
        probe_path = base / f"network-probe-{job}.json"
        require(probe_path.is_file() and digest(probe_path) == network_probe_receipts.get(job),
                f"{harness}: {job} egress-probe receipt missing/changed")
        probe = json.loads(probe_path.read_text())
        require(probe.get("status") == "pass" and probe.get("harness") == harness
                and probe.get("task") == NETWORK_PROBE_TASK
                and probe.get("network_policy") == expected_network_policy
                and probe.get("task_copy_sha256") == task_copy_digest
                and probe.get("task_config_sha256") == manifest_tasks[NETWORK_PROBE_TASK].get("task_toml_sha256")
                and probe.get("checked_hosts") == NETWORK_PROBE_HOSTS
                and probe.get("checked_host_count") == len(NETWORK_PROBE_HOSTS)
                and probe.get("relay_reachable") is True
                and probe.get("vendor_reachable") == 0 and probe.get("other_reachable") == 0,
                f"{harness}: {job} egress-probe did not confirm relay-only reachability")
        require(audit.get("network_probe_status") == "pass"
                and audit.get("network_probe_task") == NETWORK_PROBE_TASK
                and audit.get("network_probe_hosts_checked") == len(NETWORK_PROBE_HOSTS)
                and audit.get("network_probe_relay_reachable") is True
                and audit.get("network_probe_vendor_reachable") == 0
                and audit.get("network_probe_other_reachable") == 0
                and audit.get("network_probe_receipt_sha256") == digest(probe_path),
                f"{harness}: {job} audit does not bind the egress-probe receipt")
        require(settings.get("effort", {}).get(job) == audit.get("effort")
                and settings.get("concurrency", {}).get(job) == audit.get("concurrency")
                and settings.get("environment", {}).get(job) == audit.get("environment")
                and settings.get("allowed_host_count", {}).get(job) == audit.get("allowed_host_count")
                and settings.get("timeout_multiplier", {}).get(job) == audit.get("timeout_multiplier")
                and settings.get("agent_timeout_multiplier", {}).get(job) == audit.get("agent_timeout_multiplier"),
                f"{harness}: receipt settings do not match audited job config")
    require(audits_match_memory := (json.loads((base / f"audit-config-{mem_job}.json").read_text()).get("memory_sha256") == mem_digest),
            f"{harness}: memory audit digest differs from selected generation")

    server_log = Path(f"/tmp/fm-c2-{__import__('os').environ['USER']}/ollama-{gate_id}/server.log")
    relay_log = server_log.with_name("relay.log")
    log_hashes = receipt.get("serving_log_sha256") or {}
    require(server_log.is_file() and digest(server_log) == log_hashes.get("server"), f"{harness}: Ollama log changed/missing")
    require(relay_log.is_file() and digest(relay_log) == log_hashes.get("relay"), f"{harness}: relay log changed/missing")
    gate_log = ROOT / "official/logs/cluster2" / f"gate-{gate_id}.log"
    require(gate_log.is_file() and digest(gate_log) == receipt.get("gate_log_sha256"), f"{harness}: gate log changed/missing")

    posthoc = receipt.get("posthoc_correction")
    if posthoc is not None:
        require(harness == "hermes" and gate_id == POSTHOC_GATE_ID and isinstance(posthoc, dict),
                f"{harness}: unexpected post-hoc gate correction")
        executed_commit = posthoc.get("executed_commit")
        require(executed_commit == POSTHOC_EXECUTED_COMMIT
                and receipt.get("task_execution_commit") == POSTHOC_EXECUTED_COMMIT
                and git("merge-base", "--is-ancestor", executed_commit, gate_commit) == "",
                f"{harness}: post-hoc execution commit is not an ancestor")
        require(posthoc.get("validator_commit") == gate_commit,
                f"{harness}: post-hoc validator commit differs")
        require(posthoc.get("changed_files") == sorted(POSTHOC_VALIDATOR_FILES)
                and posthoc.get("task_prefix_lines_unchanged") == POST_TASK_PREFIX_LINES,
                f"{harness}: post-hoc scope receipt differs")
        changed = set(git("diff", "--name-only", f"{executed_commit}..{gate_commit}").splitlines())
        require(changed == POSTHOC_VALIDATOR_FILES,
                f"{harness}: post-hoc changes exceed the validator allowlist")
        old_gate = git("show", f"{executed_commit}:official/vm/next-gate-cluster2.sh")
        new_gate = (ROOT / "official/vm/next-gate-cluster2.sh").read_text()
        require(old_gate.splitlines()[:POST_TASK_PREFIX_LINES]
                == new_gate.splitlines()[:POST_TASK_PREFIX_LINES],
                f"{harness}: post-hoc correction changed task-launch code")

    if require_prereg:
        tag_commit = git("rev-parse", "refs/tags/prereg-c2^{commit}")
        require(git("merge-base", "--is-ancestor", tag_commit, "HEAD") == "",
                "prereg-c2 tag must be an ancestor of HEAD")
        require(subprocess.run(["git", "cat-file", "-e", "refs/tags/prereg-c2:results/preregistration-cluster2.md"],
                               cwd=ROOT).returncode == 0, "tag does not contain cluster2 preregistration")
        post_tag = set(git("diff", "--name-only", "refs/tags/prereg-c2..HEAD").splitlines())
        require(post_tag <= {"results/preregistration-cluster2.md", "results/decisions-log-cluster2.md"},
                f"{harness}: code or environment changed after preregistration tag")
        changed = set(git("diff", "--name-only", f"{gate_commit}..HEAD").splitlines())
        require(changed <= {"results/preregistration-cluster2.md", "results/decisions-log-cluster2.md"},
                f"{harness}: code or environment changed after its gate")
    if posthoc is None:
        if not require_prereg:
            require(git("rev-parse", "HEAD") == gate_commit, f"{harness}: source changed after gate")
        failed = ROOT / f"official/vm/GATE_FAILED_{slug}_CLUSTER2"
        require(not failed.exists(), f"{harness}: unresolved failed gate marker exists")
    else:
        if not require_prereg:
            require(git("rev-parse", "HEAD") == gate_commit,
                    f"{harness}: post-hoc validator source changed after finalization")
        else:
            changed = set(git("diff", "--name-only", f"{gate_commit}..HEAD").splitlines())
            require(changed <= {"results/preregistration-cluster2.md", "results/decisions-log-cluster2.md"},
                    f"{harness}: code or environment changed after post-hoc finalization")
        failed = ROOT / "official/vm/GATE_FAILED_HERMES_CLUSTER2"
        require(failed.is_file() and digest(failed) == posthoc.get("failed_marker_sha256")
                and failed.read_text().strip() == "wrong or missing model route",
                "hermes: original route-check failure marker missing or changed")
        raw_log = gate_log.read_bytes()
        line = posthoc.get("correction_line")
        expected_line = ("POSTHOC_GATE_CORRECTION type=ollama_metadata_route_allowlist "
                         f"gate={POSTHOC_GATE_ID} executed_commit={POSTHOC_EXECUTED_COMMIT} "
                         f"validator_commit={gate_commit} routes=/api/show:10,/v1/responses:245 "
                         "original_failure=wrong_or_missing_model_route")
        require(line == expected_line and raw_log.endswith((line + "\n").encode())
                and raw_log.count((line + "\n").encode()) == 1,
                "hermes: post-hoc correction line missing or duplicated")
        pre_log = raw_log[:-(len(line.encode()) + 1)]
        require(hashlib.sha256(pre_log).hexdigest() == posthoc.get("pre_correction_log_sha256"),
                "hermes: original gate log prefix changed")
        require(posthoc.get("route_counts") == routes
                and routes == {"/api/show": 10, "/v1/responses": 245},
                "hermes: post-hoc model route counts differ")
    print(f"GATE_RECEIPT_OK harness={harness} gate={gate_id}")
    return task_copy_digest


def main() -> int:
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--harness", choices=HARNESSES)
    g.add_argument("--all", action="store_true")
    p.add_argument("--require-prereg", action="store_true")
    args = p.parse_args()
    try:
        require(ROOT.is_dir() and git("branch", "--show-current") == "cluster2", "wrong worktree or branch")
        require(not git("status", "--porcelain"), "worktree is not clean")
        require(git("rev-parse", "origin/main:HANDOFF-updates.md") == UPDATE, "handoff update changed")
        digests = [check_one(harness, args.require_prereg)
                   for harness in (HARNESSES if args.all else (args.harness,))]
        if args.all:
            require(len(set(digests)) == 1,
                    "Hermes, Codex, and Claude Code gates used different task-copy digests")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"GATE_PREREQUISITE_FAILED: {exc}")
        return 1
    print("ALL_HARNESS_GATES_OK" if args.all or args.require_prereg else "GATE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
