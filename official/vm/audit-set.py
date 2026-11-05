#!/usr/bin/env python3
"""Fail-closed, count-only audit of one task-agent set inside the private VM."""
from __future__ import annotations
import argparse, collections, hashlib, json, math, re, tomllib
from pathlib import Path
import yaml

TASKS = frozenset("""
apex-brightpath-market-share apex-brightpath-seat-surplus apex-eurogrid-curtailment
automationbench-marketing-content-gap-analysis automationbench-sales-chatgpt-proposal-customization
automationbench-sales-partnership-contract awilix-release-tier-explicit awilix-release-tier-implicit
build-word2vec-pipeline cattrs-compositional-changelog cookie-store-compositional-changelog
customer-delivery-contextual-preferences dapt-intrusion-detection-workflow-learning
enterpriseops-csm-26d1b04a enterpriseops-teams-2725d17f
""".split())
MODEL = "qwen3.8:27b-mtp-q4_K_M"
NETWORK_PROBE_TASK = "dapt-intrusion-detection-workflow-learning"
NETWORK_POLICY = "agent.network_mode=allowlist;agent.allowed_hosts=10.0.2.2"
NETWORK_PROBE_HOSTS = {
    "10.0.2.2": True,
    "api.anthropic.com": False,
    "api.openai.com": False,
    "example.com": False,
    "github.com": False,
}
ADAPTERS = {
    "hermes": "fm_local.hermes_local:LocalHermes",
    "codex": "fm_local.codex_local:LocalCodex",
    "claude-code": "fm_local.claude_code_local:LocalClaudeCode",
    "exposure-none": "fm_local.exposure_hermes:ExposureHermes",
    "exposure-all": "fm_local.exposure_hermes:ExposureHermes",
    "delivery-cue": "fm_local.delivery_hermes:CueHermes",
    "delivery-scoped": "fm_local.delivery_hermes:ScopedHermes",
    "delivery-categorized": "fm_local.delivery_hermes:CategorizedHermes",
}
HERMES_HARNESSES = {"hermes", "exposure-none", "exposure-all", "delivery-cue", "delivery-scoped", "delivery-categorized"}
HERMES_UNAVAILABLE = ("didn't respond in time", "provider has been unresponsive")
OTHER_UNAVAILABLE = (*HERMES_UNAVAILABLE, "connection refused", "could not connect", "model_unavailable",
                     "econnrefused", "socket hang up", "upstream unreachable")

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()

def task_tree_sha256(root: Path) -> str:
    files = []
    for item in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        relative = item.relative_to(root).as_posix()
        if item.is_symlink():
            digest = hashlib.sha256(str(item.readlink()).encode()).hexdigest()
            kind = "symlink"
        elif item.is_file():
            digest = sha(item)
            kind = "file"
        else:
            continue
        files.append({"path": relative, "kind": kind, "sha256": digest})
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()

def scan_texts(trial: Path, harness: str):
    agent_dir = trial / "agent"
    paths = [agent_dir / "hermes.txt"] if harness in HERMES_HARNESSES else agent_dir.rglob("*")
    for p in paths:
        if p.is_file() and p.stat().st_size <= 8 * 1024 * 1024:
            try: yield p.read_text(errors="ignore")
            except OSError: pass

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("job", type=Path)
    p.add_argument("--harness", choices=sorted(ADAPTERS), required=True)
    p.add_argument("--kind", choices=("control", "memory", "exposure"), required=True)
    p.add_argument("--environment", choices=("docker", "modal"), required=True,
                   help="Harbor environment selected by frontier-memory run-tasks")
    p.add_argument("--attempts", type=int, required=True)
    p.add_argument("--tasks", nargs="+", choices=sorted(TASKS))
    p.add_argument("--expected-memory")
    p.add_argument("--expected-arm")
    p.add_argument("--network-probe-receipt", type=Path)
    p.add_argument("--task-copy-root", type=Path, required=True)
    p.add_argument("--task-copy-manifest", type=Path, required=True)
    p.add_argument("--json-out", type=Path)
    p.add_argument("--allow-model-unavailable", action="store_true",
                   help="count rewarded model-unavailable trials without failing a counted set audit")
    a = p.parse_args()
    errors = []
    task_copy_digest = None
    task_copy_manifest_sha256 = None
    try:
        if a.task_copy_root != Path("data/tasks-fm-cluster2") or a.task_copy_manifest != Path("data/tasks-fm-cluster2.manifest.json"):
            raise ValueError("task-copy paths differ from the dedicated cluster2 copy")
        manifest = json.loads(a.task_copy_manifest.read_text())
        manifest_tasks = manifest.get("tasks")
        if (manifest.get("status") != "pass" or manifest.get("network_policy") != NETWORK_POLICY
                or manifest.get("task_count") != len(TASKS) or not isinstance(manifest_tasks, dict)
                or set(manifest_tasks) != TASKS):
            raise ValueError("task-copy manifest metadata differs")
        canonical = json.dumps(manifest_tasks, sort_keys=True, separators=(",", ":")).encode()
        task_copy_digest = hashlib.sha256(canonical).hexdigest()
        if task_copy_digest != manifest.get("task_copy_sha256"):
            raise ValueError("task-copy manifest digest differs")
        for task in sorted(TASKS):
            task_toml = a.task_copy_root / task / "task.toml"
            raw = task_toml.read_bytes()
            if hashlib.sha256(raw).hexdigest() != manifest_tasks[task].get("task_toml_sha256"):
                raise ValueError(f"task-copy TOML digest differs: {task}")
            config = tomllib.loads(raw.decode("utf-8"))
            policy = config.get("agent") or {}
            if policy.get("network_mode") != "allowlist" or policy.get("allowed_hosts") != ["10.0.2.2"]:
                raise ValueError(f"task-agent network policy differs: {task}")
            if task_tree_sha256(a.task_copy_root / task) != manifest_tasks[task].get("tree_sha256"):
                raise ValueError(f"task-copy content digest differs: {task}")
        task_copy_manifest_sha256 = sha(a.task_copy_manifest)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        errors.append(f"cluster2 relay-only task copy failed validation: {exc}")
    config_path = a.job / "config.json"
    cfg = json.loads(config_path.read_text())
    agents = cfg.get("agents") or []
    agent = agents[0] if len(agents) == 1 else {}
    if len(agents) != 1: errors.append("expected exactly one task agent")
    adapter = agent.get("import_path") or agent.get("name")
    model = agent.get("model_name") or ""
    kwargs = agent.get("kwargs") or {}
    if adapter != ADAPTERS[a.harness]: errors.append("configured adapter differs")
    if not model.endswith(MODEL): errors.append("configured local model differs")
    if kwargs.get("reasoning_effort") != "max": errors.append("task reasoning effort is not max")
    if a.harness.startswith("exposure-") and kwargs.get("exposure") != a.expected_arm:
        errors.append("configured exposure arm differs")
    if a.harness.startswith("delivery-") and kwargs.get("delivery") != a.expected_arm:
        errors.append("configured delivery arm differs")
    if cfg.get("n_concurrent_trials") != 1: errors.append("task concurrency differs from single-server limit")
    if cfg.get("n_attempts") not in (None, a.attempts): errors.append("configured attempts differ")
    timeout_values = {}
    for field in ("timeout_multiplier", "agent_timeout_multiplier"):
        value = cfg.get(field, 1)
        if value is None:
            value = 1
        timeout_values[field] = value
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value != 1:
            errors.append(f"{field} differs from full-limit setting")
    # Harbor's run-tasks CLI accepts -e/--env but does not serialize that
    # runtime selector into the generated job config.json. The launcher passes
    # the same value used to build TASK_COMMON into this audit.
    if "environment" not in cfg:
        env_config = {}
    else:
        env_config = cfg["environment"]
    if "environment" in cfg and not isinstance(env_config, dict):
        errors.append("saved environment config is malformed")
        env_config = {}
    env_type = a.environment
    agent_hosts = agent.get("extra_allowed_hosts") or []
    environment_hosts = env_config.get("extra_allowed_hosts") or []
    if "environment" in cfg and env_config.get("type") != env_type:
        errors.append("configured environment differs from selected Harbor environment")
    if env_type != "docker": errors.append("task environment is not Docker")
    if set(agent_hosts) != {"10.0.2.2"}: errors.append("agent egress allowlist differs from relay-only route")
    if environment_hosts: errors.append("environment egress allowlist is not empty")
    verifier = (cfg.get("verifier") or {}).get("env") or {}
    template = str(verifier.get("ANTHROPIC_API_KEY", ""))
    if "JUDGE_ANTHROPIC_KEY" not in template: errors.append("judge key is not verifier-only")

    network_probe = None
    network_probe_sha256 = None
    if a.network_probe_receipt is None:
        errors.append("effective-egress probe receipt is missing")
    else:
        try:
            network_probe = json.loads(a.network_probe_receipt.read_text())
            network_probe_sha256 = sha(a.network_probe_receipt)
        except (OSError, ValueError, json.JSONDecodeError):
            errors.append("effective-egress probe receipt is unreadable")
            network_probe = None
        if isinstance(network_probe, dict):
            probe_task_config = a.task_copy_root / NETWORK_PROBE_TASK / "task.toml"
            if (network_probe.get("status") != "pass"
                    or network_probe.get("harness") != a.harness
                    or network_probe.get("task") != NETWORK_PROBE_TASK
                    or network_probe.get("network_policy") != NETWORK_POLICY
                    or network_probe.get("task_copy_sha256") != task_copy_digest
                    or network_probe.get("task_config_sha256") != sha(probe_task_config)
                    or network_probe.get("checked_hosts") != NETWORK_PROBE_HOSTS
                    or network_probe.get("checked_host_count") != len(NETWORK_PROBE_HOSTS)
                    or network_probe.get("relay_reachable") is not True
                    or network_probe.get("vendor_reachable") != 0
                    or network_probe.get("other_reachable") != 0
                    or not re.fullmatch(r"[0-9a-f]{64}", str(network_probe.get("probe_raw_sha256", "")))):
                errors.append("effective-egress probe did not confirm relay-only reachability")

    expected_tasks = set(a.tasks or TASKS)
    if not expected_tasks <= TASKS or a.attempts < 1: errors.append("invalid task/attempt selection")
    wanted = collections.Counter({t: a.attempts for t in expected_tasks})
    counts, digests, judges = collections.Counter(), set(), collections.Counter()
    unavailable_count = exposure_trials = exposure_metric_trials = delivery_metric_trials = 0
    for trial in sorted(p for p in a.job.iterdir() if p.is_dir()):
        rp = trial / "result.json"
        if not rp.is_file(): errors.append("unfinished trial directory"); continue
        result = json.loads(rp.read_text())
        task = str(result.get("task_name") or "").split("/")[-1]
        counts[task] += 1
        reward = ((result.get("verifier_result") or {}).get("rewards") or {}).get("reward")
        if isinstance(reward, bool) or not isinstance(reward, (int, float)) or not math.isfinite(reward):
            errors.append("trial has no finite verifier reward")
        metadata = (result.get("agent_result") or {}).get("metadata") or {}
        memory = metadata.get("frontier_memory") or {}
        digest = memory.get("sha256") if isinstance(memory, dict) else None
        digests.add(digest)
        if a.kind == "control" and digest is not None: errors.append("control trial has memory")
        if a.kind != "control" and not (isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest)):
            errors.append("memory digest absent or malformed")
        if a.expected_memory and digest != a.expected_memory: errors.append("memory digest differs from selected generation")
        details = trial / "verifier" / "grade_details.json"
        judge = json.loads(details.read_text()).get("grading_run_status") if details.is_file() else None
        if judge: judges[judge] += 1
        if task.startswith("apex-") and judge != "completed": errors.append("APEX judge is not complete")
        if judge not in (None, "completed"): errors.append("judge run is incomplete")
        logs = list(scan_texts(trial, a.harness))
        markers = HERMES_UNAVAILABLE if a.harness in HERMES_HARNESSES else OTHER_UNAVAILABLE
        unavailable_count += any(any(marker in text.casefold() for marker in markers) for text in logs)

        hermes_cfg_path = trial / "agent" / "hermes-config.yaml"
        if a.harness.startswith(("exposure-", "delivery-")):
            if not hermes_cfg_path.is_file():
                errors.append("Hermes treatment config is missing")
            else:
                hermes_cfg = yaml.safe_load(hermes_cfg_path.read_text()) or {}
                memory_enabled = (hermes_cfg.get("memory") or {}).get("memory_enabled")
                plugin_enabled = (hermes_cfg.get("plugins") or {}).get("enabled") or []
                if a.expected_arm == "none" and a.harness.startswith("exposure-") and memory_enabled is not False:
                    errors.append("E-none Hermes memory block is enabled")
                if a.expected_arm == "all" and a.harness.startswith("exposure-"):
                    if memory_enabled is not True or not (hermes_cfg.get("agent") or {}).get("system_prompt"):
                        errors.append("E-all Hermes treatment config differs")
                if a.expected_arm == "cue" and memory_enabled is not False:
                    errors.append("cue Hermes memory block is enabled")
                if a.harness.startswith("delivery-"):
                    if "fm-delivery-c2" not in plugin_enabled:
                        errors.append("delivery plugin is not enabled")
                if a.harness.startswith("exposure-") and "fm-delivery-c2" not in plugin_enabled:
                    errors.append("exposure index observer plugin is not enabled")

        if a.harness.startswith("exposure-"):
            exposure = metadata.get("fm_exposure") or {}
            exposure_trials += 1
            if exposure.get("exposure") != a.expected_arm or exposure.get("memory_sha256") != digest:
                errors.append("exposure arm/digest metadata differs")
            if a.expected_arm == "none" and (exposure.get("memory_block_shown") is not False or exposure.get("skills_index_shown") is not False):
                errors.append("E-none treatment metadata differs")
            if a.expected_arm == "all" and (exposure.get("memory_block_shown") is not True or exposure.get("skills_index_shown") is not True
                    or not isinstance(exposure.get("injected_bytes"), int) or exposure["injected_bytes"] <= 0):
                errors.append("E-all treatment metadata differs")
            report_path = trial / "agent" / "exposure-report.json"
            if not report_path.is_file():
                errors.append("saved exposure report is missing")
            else:
                report = json.loads(report_path.read_text())
                if report.get("exposure") != a.expected_arm or report.get("memory_sha256") != digest:
                    errors.append("saved exposure report differs")
            records = []
            for text in logs:
                for line in text.splitlines():
                    if "FM_DELIVERY_METRICS=" in line:
                        try: records.append(json.loads(line.split("FM_DELIVERY_METRICS=", 1)[1].strip()))
                        except json.JSONDecodeError: errors.append("exposure observer metrics malformed")
            if len(records) != 1:
                errors.append("exposure observer metrics missing or duplicated")
            else:
                m = records[0]; exposure_metric_trials += 1
                if m.get("delivery") != "observe" or m.get("memory_sha256") != digest:
                    errors.append("exposure observer arm/digest differs")
                if m.get("first_request_seen") is not True:
                    errors.append("exposure observer did not see a model request")
                if a.expected_arm == "none" and (m.get("initial_memory_bytes") != 0
                        or m.get("memory_skills_index_file_count") != 0
                        or m.get("memory_index_entries_observed") != 0):
                    errors.append("E-none memory block or memory skill index was observed")
                if a.expected_arm == "all" and (m.get("initial_memory_bytes") != exposure.get("memory_md_bytes")
                        or m.get("memory_skills_index_file_count") != exposure.get("skill_files")
                        or m.get("memory_index_entries_observed") != exposure.get("skill_files")
                        or not isinstance(m.get("memory_index_entry_bytes_observed"), int)):
                    errors.append("E-all ordinary HM startup exposure was not fully observed")
        if a.harness.startswith("delivery-"):
            delivery = metadata.get("fm_delivery") or {}
            if delivery.get("delivery") != a.expected_arm or delivery.get("memory_sha256") != digest:
                errors.append("delivery arm/digest metadata differs")
            if not isinstance(delivery.get("skill_files"), int): errors.append("delivery skill count absent")
            report_path = trial / "agent" / "delivery-report.json"
            if not report_path.is_file():
                errors.append("saved delivery report is missing")
            else:
                report = json.loads(report_path.read_text())
                if report.get("delivery") != a.expected_arm or report.get("memory_sha256") != digest:
                    errors.append("saved delivery report differs")
            if a.expected_arm == "scoped" and delivery.get("skills_index_filtered") is not True:
                errors.append("scoped skills index was not filtered")
            records = []
            for text in logs:
                for line in text.splitlines():
                    if "FM_DELIVERY_METRICS=" in line:
                        try: records.append(json.loads(line.split("FM_DELIVERY_METRICS=", 1)[1].strip()))
                        except json.JSONDecodeError: errors.append("delivery metrics malformed")
            if len(records) != 1:
                errors.append("delivery plugin metrics missing or duplicated")
            else:
                m = records[0]; delivery_metric_trials += 1
                if m.get("delivery") != a.expected_arm or m.get("memory_sha256") != digest:
                    errors.append("delivery plugin arm/digest differs")
                if m.get("first_request_seen") is not True:
                    errors.append("delivery did not observe a model request")
                if m.get("memory_skills_index_file_count") != delivery.get("skills_selected"):
                    errors.append("uploaded memory skills index count differs from the adapter report")
                if m.get("memory_index_entries_observed") != delivery.get("skills_selected"):
                    errors.append("request-visible memory skill count differs from the adapter report")
                if a.expected_arm == "cue" and (m.get("initial_memory_bytes") != 0 or m.get("memory_skills_index_file_count") != 0
                        or m.get("memory_index_entries_observed") != 0):
                    errors.append("cue arm showed memory/index at start")
                if a.expected_arm == "scoped" and delivery.get("skills_selected", 0) > 0 and m.get("memory_index_entry_bytes_observed", 0) <= 0:
                    errors.append("scoped memory skills were not observed in the request")
                if a.expected_arm == "cue":
                    if m.get("tool_result_insertions", 0) > m.get("cue_activations", 0):
                        errors.append("cue insertion count exceeds activation count")
                    if m.get("confirmed_next_request_exposures", 0) > m.get("tool_result_insertions", 0):
                        errors.append("confirmed cue exposure exceeds insertion count")
                if a.expected_arm == "categorized":
                    if m.get("categorized_index_rewrites", 0) < 1:
                        errors.append("categorized index was not rewritten")
                    if (m.get("categorized_index_integrity_ok") is not True
                            or m.get("categorized_index_integrity_checks") != m.get("categorized_index_rewrites")
                            or m.get("categorized_memory_entries_before") != delivery.get("skills_selected")
                            or m.get("categorized_memory_entries_after") != delivery.get("skills_selected")
                            or m.get("categorized_index_memory_entries_observed") != delivery.get("skills_selected")
                            or m.get("categorized_index_memory_entry_bytes_observed", 0) <= 0
                            or m.get("categorized_index_category_header_bytes_observed", 0) <= 0
                            or m.get("categorized_bundled_entries_before") != m.get("categorized_bundled_entries_after")
                            or m.get("categorized_nonmemory_inventory_sha256_before")
                            != m.get("categorized_nonmemory_inventory_sha256_after")):
                        errors.append("categorized rewrite changed or duplicated bundled or memory skill entries")
        tp = trial / "config.json"
        if tp.is_file():
            tc = json.loads(tp.read_text()); ta = tc.get("agent") or {}
            timeout = ta.get("override_timeout_sec") or ta.get("timeout_sec")
            if timeout is not None and (not isinstance(timeout, (int, float)) or timeout <= 0):
                errors.append("trial timeout is invalid")

    if counts != wanted: errors.append("task identities or attempt counts differ")
    if a.kind == "control" and digests - {None}: errors.append("control digest set is not empty")
    if a.kind != "control" and len(digests) != 1: errors.append("memory digests are inconsistent")
    if unavailable_count and not a.allow_model_unavailable:
        errors.append("model_unavailable signal found in agent logs")
    if a.harness.startswith("exposure-") and exposure_trials != sum(counts.values()):
        errors.append("exposure treatment missing in a trial")
    if a.harness.startswith("exposure-") and exposure_metric_trials != sum(counts.values()):
        errors.append("exposure observer metrics missing in a trial")
    if a.harness.startswith("delivery-") and delivery_metric_trials != sum(counts.values()):
        errors.append("delivery plugin metrics missing in a trial")

    config_sha = sha(config_path)
    report = {
        "status": "pass" if not errors else "fail", "harness": a.harness, "adapter": adapter, "model": model,
        "effort": kwargs.get("reasoning_effort"),
        "kind": a.kind, "expected_arm": a.expected_arm, "expected_memory": a.expected_memory,
        "attempts": a.attempts, "trial_count": sum(counts.values()), "task_count": len(counts),
        "memory_sha256": sorted(d for d in digests if d), "environment": env_type,
        "network_policy": NETWORK_POLICY, "task_copy_sha256": task_copy_digest,
        "task_copy_manifest_sha256": task_copy_manifest_sha256,
        "allowed_host_count": len(agent_hosts), "environment_allowed_host_count": len(environment_hosts),
        "timeout_multiplier": timeout_values["timeout_multiplier"],
        "agent_timeout_multiplier": timeout_values["agent_timeout_multiplier"],
        "concurrency": cfg.get("n_concurrent_trials"), "config_sha256": config_sha,
        "network_probe_status": network_probe.get("status") if isinstance(network_probe, dict) else None,
        "network_probe_task": network_probe.get("task") if isinstance(network_probe, dict) else None,
        "network_probe_hosts_checked": network_probe.get("checked_host_count") if isinstance(network_probe, dict) else None,
        "network_probe_relay_reachable": network_probe.get("relay_reachable") if isinstance(network_probe, dict) else None,
        "network_probe_vendor_reachable": network_probe.get("vendor_reachable") if isinstance(network_probe, dict) else None,
        "network_probe_other_reachable": network_probe.get("other_reachable") if isinstance(network_probe, dict) else None,
        "network_probe_receipt_sha256": network_probe_sha256,
        "model_unavailable": unavailable_count, "judge_statuses": dict(judges),
        "errors": sorted(set(errors)),
    }
    print(f"AUDIT_CONFIG sha256={config_sha} environment={env_type} agent_allowed_hosts={len(agent_hosts)} "
          f"environment_allowed_hosts={len(environment_hosts)} attempts={cfg.get('n_attempts')} "
          f"timeout_multiplier={cfg.get('timeout_multiplier', 1)} agent_timeout_multiplier={cfg.get('agent_timeout_multiplier', 1)} "
          f"concurrency={cfg.get('n_concurrent_trials')}")
    print(f"AUDIT agent={adapter} model={model} effort={kwargs.get('reasoning_effort')} trials={sum(counts.values())} "
          f"tasks={len(counts)} memory_digest_count={len(digests - {None})} model_unavailable={unavailable_count} judges={dict(judges)}")
    if a.json_out: a.json_out.write_text(json.dumps(report, sort_keys=True, indent=1) + "\n")
    if errors:
        print("AUDIT_FAILED: " + "; ".join(sorted(set(errors))))
        return 1
    print("AUDIT_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
