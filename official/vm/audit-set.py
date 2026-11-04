"""Soundness audit of one set, run inside the guest. Counts and settings only; no task or memory text.

Usage (in guest): sudo python3 audit-set.py jobs/fm-tasks-control
"""

import collections
import json
import sys
from pathlib import Path

job = Path(sys.argv[1])
cfg = json.loads((job / "config.json").read_text())
print("job config: n_concurrent", cfg.get("n_concurrent_trials"), "| timeout_multiplier", cfg.get("timeout_multiplier"),
      "agent_timeout_multiplier", cfg.get("agent_timeout_multiplier"), "| attempts", cfg.get("n_attempts"))
agent = (cfg.get("agents") or [{}])[0]
print("agent:", agent.get("import_path") or agent.get("name"), "| model", agent.get("model_name"),
      "| kwargs", {k: v for k, v in (agent.get("kwargs") or {}).items() if k != "memory_dir"}, "| memory_dir", (agent.get("kwargs") or {}).get("memory_dir"))
env = cfg.get("environment") or {}
print("environment:", env.get("type"), "| extra_allowed_hosts", env.get("extra_allowed_hosts"))
ve = (cfg.get("verifier") or {}).get("env") or {}
print("verifier env keys:", sorted(ve), "| GRADING_MODEL", ve.get("GRADING_MODEL"),
      "| ANTHROPIC_API_KEY is template", str(ve.get("ANTHROPIC_API_KEY", "")).startswith("${"))
c = collections.Counter(); per = collections.defaultdict(list); issues = []
for t in sorted(p for p in job.iterdir() if p.is_dir()):
    r = t / "result.json"
    if not r.exists():
        c["unfinished"] += 1; continue
    d = json.loads(r.read_text())
    task = d.get("task_name", "").split("/")[-1]
    rew = ((d.get("verifier_result") or {}).get("rewards") or {}).get("reward")
    exc = (d.get("exception_info") or {}).get("exception_type")
    md = ((d.get("agent_result") or {}).get("metadata") or {}).get("frontier_memory")
    tcfg = json.loads((t / "config.json").read_text())
    to = (tcfg.get("agent") or {}).get("override_timeout_sec") or (tcfg.get("agent") or {}).get("timeout_sec")
    hc = t / "agent" / "hermes-config.yaml"
    hcs = hc.read_text() if hc.exists() else ""
    eff = next((l.split(":", 1)[1].strip() for l in hcs.splitlines() if "reasoning_effort" in l), None)
    mem_on = next((l.split(":", 1)[1].strip() for l in hcs.splitlines() if "memory_enabled" in l), None)
    sess = t / "agent" / "hermes-session.jsonl"
    model = json.loads(sess.read_text().splitlines()[0]).get("model") if sess.exists() and sess.read_text().strip() else None
    gd = t / "verifier" / "grade_details.json"
    judge = json.loads(gd.read_text()).get("grading_run_status") if gd.exists() else None
    log = t / "agent" / "hermes.txt"
    gave = log.exists() and "didn't respond in time" in log.read_text(errors="ignore")
    c["trials"] += 1; c[f"exception={exc}"] += 1; c[f"effort={eff}"] += 1; c[f"memory_enabled={mem_on}"] += 1; c[f"model={model}"] += 1
    if judge: c[f"judge={judge}"] += 1
    if gave: c["gave_up"] += 1
    if rew is None: issues.append(f"{t.name}: no reward")
    if md not in (None,) and "control" in job.name: issues.append(f"{t.name}: control trial has memory {md}")
    if "control" not in job.name and not isinstance(md, dict): issues.append(f"{t.name}: memory trial without memory digest")
    if judge not in (None, "completed"): issues.append(f"{t.name}: judge {judge}")
    per[task].append(rew)
print(dict(sorted(c.items())))
print("attempts per task:", {k: len(v) for k, v in sorted(per.items())})
print("ISSUES:", issues or "none")
