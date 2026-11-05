#!/bin/bash
# Counted cluster2 driver. It only runs after the tagged preregistration and all
# harness-specific full gates have passed.
set -Eeuo pipefail

REPO=$(realpath "$HOME/frontiermemory-cluster2")
cd "$REPO"
: "${SLURM_JOB_ID:?Set a unique cluster2 run id}"
[[ "$SLURM_JOB_ID" =~ ^c2-[A-Za-z0-9_-]+$ ]] || { echo BAD_RUN_ID; exit 1; }
OLOG=/tmp/fm-c2-$USER/ollama-$SLURM_JOB_ID
LOGF=$REPO/official/logs/cluster2/study-$SLURM_JOB_ID.log
RES=$REPO/results/official-cluster2
ANALYSIS=$RES/$SLURM_JOB_ID/analysis-inputs

bash official/vm/check-updates-cluster2.sh || exit 1
source official/vm/lib-cluster2.sh
acquire_study_lock || exit 1
mkdir -p "$REPO/official/logs/cluster2" "$RES"
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $*"; }
gpus_free() { for _ in $(seq 1 12); do python3 official/vm/gpu-check-cluster2.py && return 0; sleep 5; done; return 1; }
stop() { step "STUDY_STOPPED: $*"; echo "$(date) $*" > official/vm/STUDY_STOPPED_CLUSTER2; exit 1; }
[ ! -f official/vm/STUDY_STOPPED_CLUSTER2 ] || stop "prior stop marker exists; inspect before resuming"
python3 scripts/check_gate_cluster2.py --all --require-prereg || stop "gate or preregistration receipt failed"
TASK_COPY_SHA256=$(python3 - <<'PY'
import json, re
from pathlib import Path
marker = Path("official/vm/GATE_PASSED_HERMES_CLUSTER2")
parts = marker.read_text().split()
if len(parts) != 2:
    raise SystemExit("HERMES_GATE_MARKER_INVALID")
receipt = json.loads(Path(parts[0]).read_text())
digest = receipt.get("task_copy_sha256")
if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
    raise SystemExit("GATE_TASK_COPY_DIGEST_INVALID")
print(digest)
PY
) || stop "gate task-copy digest unavailable"

trials_ok() {
  python3 - "$RES/$SLURM_JOB_ID/$1/summary-$1.jsonl" "$2" <<'PY'
import collections, json, sys
try:
    rows = [json.loads(line) for line in open(sys.argv[1])]
except (OSError, json.JSONDecodeError):
    print("TRIALS: FAIL: no summary")
    sys.exit(1)
bad = []
if len(rows) != int(sys.argv[2]):
    bad.append(f"{len(rows)} trials, expected {sys.argv[2]}")
for key, label in (("valid", "invalid"), ("finished", "unfinished")):
    n = sum(r.get(key) is not True for r in rows)
    if n:
        bad.append(f"{n} {label}")
n = sum(not isinstance(r.get("model_unavailable"), bool) for r in rows)
if n:
    bad.append(f"{n} missing model-availability status")
unavailable = sum(r.get("model_unavailable") is True for r in rows)
judges = collections.Counter(r.get("judge_status") for r in rows if r.get("judge_status"))
print(f"trials={len(rows)} passed={sum(bool(r.get('passed')) for r in rows)} model_unavailable={unavailable} judge={dict(judges)}")
print("TRIALS:", "ok" if not bad else "FAIL: " + "; ".join(bad))
sys.exit(bool(bad))
PY
}

run_checked() {
  local label=$1 summary_name=$2 expected=$3 kind=$4 harness=$5 memory_digest=$6 task=$7 arm=$8
  shift 8
  bash official/vm/check-updates-cluster2.sh || stop "$label: main handoff update requires review"
  local set_dir="$RES/$SLURM_JOB_ID/$summary_name"
  local summary="$set_dir/summary-$summary_name.jsonl"
  local audit="$set_dir/audit-$summary_name.txt"
  local audit_config="$set_dir/audit-config-$summary_name.json"
  local serving="$set_dir/serving-check.txt"
  local status="$set_dir/set-check-$summary_name.json"
  local memory_access="$set_dir/memory-access-$summary_name.jsonl"
  local memory_access_check="$set_dir/memory-access-check-$summary_name.json"
  local validate=(python3 scripts/validate_set_cluster2.py "$summary" --kind "$kind" --attempts "$expected")
  [ "$task" = - ] || validate+=(--task "$task")
  [ -z "$memory_digest" ] || validate+=(--expected-memory "$memory_digest")
  if [ -f "$status" ] && "${validate[@]}" >/dev/null 2>&1 &&
     python3 scripts/validate_memory_access_cluster2.py "$summary" "$memory_access" --harness "$harness" \
       --kind "$kind" --receipt "$memory_access_check" --verify-receipt >/dev/null 2>&1 &&
     grep -q '^AUDIT_OK$' "$audit"; then
    if python3 - "$summary" "$audit" "$audit_config" "$serving" "$status" "$expected" "$harness" "$kind" "$memory_digest" "$task" "$arm" "$(git rev-parse HEAD)" "$memory_access" "$memory_access_check" "$TASK_COPY_SHA256" <<'PY'
import hashlib, json, sys
from pathlib import Path
summary, audit, audit_config, serving, receipt = map(Path, sys.argv[1:6])
expected, harness, kind, memory, task, arm, commit = sys.argv[6:13]
memory_access, memory_access_check = map(Path, sys.argv[13:15])
expected_task_copy = sys.argv[15]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
try:
    r = json.loads(receipt.read_text())
    a = json.loads(audit_config.read_text())
    ma = json.loads(memory_access_check.read_text())
    rows = [json.loads(x) for x in summary.read_text().splitlines() if x.strip()]
    key_logs = list(summary.parent.glob("key-audit-*.log"))
except (OSError, ValueError):
    raise SystemExit(1)
expected_hosts = {"10.0.2.2": True, "api.anthropic.com": False, "api.openai.com": False,
                  "example.com": False, "github.com": False}
expected_policy = "agent.network_mode=allowlist;agent.allowed_hosts=10.0.2.2"
task_name = summary.name.removeprefix("summary-").removesuffix(".jsonl")
manifest_path = summary.parent / f"task-copy-manifest-{task_name}.json"
probe_path = summary.parent / "network-probe.json"
try:
    manifest = json.loads(manifest_path.read_text())
    probe = json.loads(probe_path.read_text())
except (OSError, ValueError):
    network_ok = False
else:
    network_ok = (a.get("network_policy") == expected_policy
                  and isinstance(a.get("task_copy_sha256"), str)
                  and manifest.get("network_policy") == expected_policy
                  and manifest.get("task_copy_sha256") == a.get("task_copy_sha256")
                  and a.get("task_copy_manifest_sha256") == sha(manifest_path)
                  and a.get("task_copy_sha256") == expected_task_copy
                  and probe.get("status") == "pass" and probe.get("harness") == harness
                  and probe.get("task") == "dapt-intrusion-detection-workflow-learning"
                  and probe.get("network_policy") == expected_policy
                  and probe.get("task_copy_sha256") == a.get("task_copy_sha256")
                  and probe.get("checked_hosts") == expected_hosts
                  and probe.get("relay_reachable") is True and probe.get("vendor_reachable") == 0
                  and probe.get("other_reachable") == 0 and probe.get("checked_host_count") == len(expected_hosts)
                  and a.get("network_probe_status") == "pass"
                  and a.get("network_probe_receipt_sha256") == sha(probe_path)
                  and r.get("task_copy_sha256") == a.get("task_copy_sha256")
                  and r.get("task_copy_manifest_sha256") == sha(manifest_path)
                  and r.get("network_policy") == expected_policy
                  and r.get("network_probe_sha256") == sha(probe_path))
ok = (r.get("status") == "pass" and r.get("summary_sha256") == sha(summary)
      and r.get("audit_sha256") == sha(audit) and r.get("config_audit_sha256") == sha(audit_config)
      and r.get("serving_sha256") == sha(serving) and "SERVING: ok" in serving.read_text()
      and ma.get("status") == "pass" and ma.get("harness") == harness and ma.get("kind") == kind
      and ma.get("trial_count") == int(expected) and ma.get("summary_sha256") == sha(summary)
      and ma.get("memory_access_sha256") == sha(memory_access)
      and ma.get("memory_sha256") == (memory or None)
      and r.get("memory_access_sha256") == sha(memory_access)
      and r.get("memory_access_check_sha256") == sha(memory_access_check)
      and len(key_logs) == 1 and r.get("key_audit_sha256") == sha(key_logs[0])
      and "AUDIT_SAMPLE" in key_logs[0].read_text() and "AUDIT_DONE" in key_logs[0].read_text()
      and network_ok
      and r.get("cluster2_commit") == commit and r.get("harness") == harness
      and r.get("kind") == kind and r.get("memory_sha256") == (memory or None)
      and r.get("task") == (task if task != "-" else None) and r.get("arm") == (arm if arm != "-" else None)
      and len(rows) == int(expected) and all(x.get("finished") is True and x.get("valid") is True for x in rows)
      and a.get("status") == "pass" and a.get("harness") == harness and a.get("kind") == kind
      and a.get("expected_arm") == (arm if arm != "-" else None))
raise SystemExit(0 if ok else 1)
PY
    then
      step "$label: summary, audit and serving evidence revalidated"
      return 0
    fi
  fi
  gpus_free || stop "$label: GPUs not free"
  local server_before relay_before
  server_before=$(wc -l < "$OLOG/server.log" 2>/dev/null || echo 0)
  relay_before=$(wc -l < "$OLOG/relay.log" 2>/dev/null || echo 0)
  step "$label: start"
  "$@" 2>&1 | tee -a "$LOGF" || stop "$label: set command failed"
  python3 scripts/validate_memory_access_cluster2.py "$summary" "$memory_access" --harness "$harness" \
    --kind "$kind" --receipt "$memory_access_check" --verify-receipt | tee -a "$LOGF" || stop "$label: memory-access report failed validation"
  if tail -60 "$LOGF" | grep -q "NO_VALID_MEMORY"; then stop "$label: NO_VALID_MEMORY; trials not counted"; fi
  python3 official/vm/check-serving.py "$OLOG" "$server_before" "$relay_before" --summaries "$set_dir" | tee "$serving" | tee -a "$LOGF"
  [ "${PIPESTATUS[0]}" = 0 ] || stop "$label: serving check failed"
  trials_ok "$summary_name" "$expected" | tee -a "$LOGF"
  [ "${PIPESTATUS[0]}" = 0 ] || stop "$label: summary check failed"
  "${validate[@]}" || stop "$label: summary validation failed"
  grep -q '^AUDIT_OK$' "$audit" || stop "$label: audit evidence missing or failed"
  python3 - "$summary" "$audit" "$audit_config" "$serving" "$status" "$harness" "$kind" "$memory_digest" "$task" "$arm" "$(git rev-parse HEAD)" "$memory_access" "$memory_access_check" "$TASK_COPY_SHA256" <<'PY'
import hashlib, json, os, sys, tempfile
from pathlib import Path
summary, audit, audit_config, serving, out = map(Path, sys.argv[1:6])
harness, kind, memory, task, arm, commit = sys.argv[6:12]
memory_access, memory_access_check = map(Path, sys.argv[12:14])
expected_task_copy = sys.argv[14]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
ma = json.loads(memory_access_check.read_text())
audit_record = json.loads(audit_config.read_text())
if audit_record.get("task_copy_sha256") != expected_task_copy:
    raise SystemExit("SET_TASK_COPY_DIFFERS_FROM_GATES")
key_logs = list(summary.parent.glob("key-audit-*.log"))
if len(key_logs) != 1: raise SystemExit("KEY_AUDIT_RECEIPT_MISSING")
report = {"status":"pass", "summary_sha256":sha(summary), "audit_sha256":sha(audit),
          "config_audit_sha256":sha(audit_config), "serving_sha256":sha(serving),
          "key_audit_sha256":sha(key_logs[0]),
          "memory_access_sha256":sha(memory_access), "memory_access_check_sha256":sha(memory_access_check),
          "task_copy_manifest_sha256":sha(summary.parent / f"task-copy-manifest-{summary.name.removeprefix('summary-').removesuffix('.jsonl')}.json"),
          "network_probe_sha256":sha(summary.parent / "network-probe.json"),
          "task_copy_sha256":json.loads(audit_config.read_text()).get("task_copy_sha256"),
          "network_policy":json.loads(audit_config.read_text()).get("network_policy"),
          "cluster2_commit":commit, "harness":harness, "kind":kind, "memory_sha256":memory or None,
          "task":task if task != "-" else None, "arm":arm if arm != "-" else None}
fd, tmp = tempfile.mkstemp(dir=out.parent, prefix=".set-check-")
with os.fdopen(fd, "w") as f: json.dump(report, f, sort_keys=True); f.write("\n")
os.chmod(tmp, 0o600); os.replace(tmp, out)
PY
  step "$label: SET_CHECKED"
}

# Use the validated, uncounted Hermes gate generation to exercise every altered loader before A0.
read -r PREFLIGHT_MEMORY_JOB PREFLIGHT_MEMORY_DIGEST < <(python3 - "$REPO/official/vm/GATE_PASSED_HERMES_CLUSTER2" "$REPO" <<'PY'
import json, re, sys
from pathlib import Path
marker, root = Path(sys.argv[1]), Path(sys.argv[2])
parts = marker.read_text().split()
if len(parts) != 2:
    raise SystemExit("HERMES_GATE_MARKER_INVALID")
receipt = json.loads((root / parts[0]).read_text())
gate = receipt.get("gate_job")
digests = receipt.get("memory_sha256")
if (not isinstance(gate, str) or not isinstance(digests, list) or len(digests) != 1
        or not re.fullmatch(r"[0-9a-f]{64}", str(digests[0]))):
    raise SystemExit("HERMES_GATE_MEMORY_INVALID")
print(f"fm-gen-gate-hermes-{gate} {digests[0]}")
PY
) || stop "validated Hermes gate generation unavailable for treatment preflights"

for arm in none all; do
  smoke_job="fm-c2-smoke-exposure-$arm-$SLURM_JOB_ID"
  run_checked "E-$arm Word2Vec preflight" "$smoke_job" 1 exposure "exposure-$arm" "$PREFLIGHT_MEMORY_DIGEST" build-word2vec-pipeline "$arm" env EXPECTED_MEMORY="$PREFLIGHT_MEMORY_DIGEST" \
    MEMORY_JOB_NAME="$PREFLIGHT_MEMORY_JOB" TASK_JOB_NAME="$smoke_job" E2E=1 bash official/vm/run-exposure-cluster2.sh "$arm"
done

for arm in cue scoped categorized; do
  set_name="delivery-$arm"
  smoke_job="fm-c2-smoke-$set_name-$SLURM_JOB_ID"
  run_checked "$set_name Word2Vec preflight" "$smoke_job" 1 memory "$set_name" "$PREFLIGHT_MEMORY_DIGEST" build-word2vec-pipeline "$arm" env SET="$set_name-smoke" \
    TASK_HARNESS="$set_name" TASK_JOB_NAME="$smoke_job" MEMORY_SOURCE=run1 MEMORY_JOB_NAME="$PREFLIGHT_MEMORY_JOB" \
    EXPECTED_MEMORY="$PREFLIGHT_MEMORY_DIGEST" SMOKE=1 bash official/vm/run-set-cluster2.sh
done

run_checked "A0" fm-tasks-control 45 control hermes "" - - env SET=control TASK_HARNESS=hermes MEMORY_SOURCE=none \
  bash official/vm/run-set-cluster2.sh
python3 -I scripts/analyze_official.py --dir "$ANALYSIS" | tee -a "$LOGF"

for set_name in run1 run2 run3; do
  run_checked "HM $set_name" "fm-tasks-$set_name" 45 memory hermes "" - - env SET="$set_name" TASK_HARNESS=hermes MEMORY_SOURCE=generate \
    bash official/vm/run-set-cluster2.sh
  python3 -I scripts/analyze_official.py --dir "$ANALYSIS" | tee -a "$LOGF"
done

HM1_DIGEST=$(python3 - "$RES/$SLURM_JOB_ID/fm-tasks-run1/summary-fm-tasks-run1.jsonl" <<'PY'
import json, re, sys
rows = [json.loads(line) for line in open(sys.argv[1])]
digests = {row.get("memory_sha256") for row in rows}
if len(rows) != 45 or len(digests) != 1 or not re.fullmatch(r"[0-9a-f]{64}", next(iter(digests), "")):
    raise SystemExit("HM1_DIGEST_UNAVAILABLE")
print(next(iter(digests)))
PY
) || stop "HM1 memory digest unavailable"

for arm in none all; do
  run_checked "E-$arm" "fm-tasks-exposure-$arm" 45 exposure "exposure-$arm" "$HM1_DIGEST" - "$arm" env EXPECTED_MEMORY="$HM1_DIGEST" \
    bash official/vm/run-exposure-cluster2.sh "$arm"
  python3 scripts/analyze_arms_cluster2.py --arm "E-$arm" --summary "fm-tasks-exposure-$arm" --dir "$ANALYSIS" | tee -a "$LOGF"
done

for arm in codex-c0 codex-cm claude-k0 claude-km; do
  case "$arm" in
    codex-c0) harness=codex; memory_source=none; memory_digest= ;;
    codex-cm) harness=codex; memory_source=run1; memory_digest=$HM1_DIGEST ;;
    claude-k0) harness=claude-code; memory_source=none; memory_digest= ;;
    claude-km) harness=claude-code; memory_source=run1; memory_digest=$HM1_DIGEST ;;
  esac
  kind=memory
  [ "$memory_source" = none ] && kind=control
  run_checked "$arm" "fm-tasks-$arm" 45 "$kind" "$harness" "$memory_digest" - - env SET="$arm" TASK_HARNESS="$harness" \
    MEMORY_SOURCE="$memory_source" MEMORY_JOB_NAME=fm-gen-run1 EXPECTED_MEMORY="$memory_digest" \
    bash official/vm/run-set-cluster2.sh
  python3 scripts/analyze_arms_cluster2.py --arm "$arm" --summary "fm-tasks-$arm" --dir "$ANALYSIS" | tee -a "$LOGF"
done

for arm in cue scoped categorized; do
  set_name="delivery-$arm"
  run_checked "$set_name" "fm-tasks-$set_name" 45 memory "$set_name" "$HM1_DIGEST" - "$arm" env SET="$set_name" TASK_HARNESS="$set_name" \
    MEMORY_SOURCE=run1 MEMORY_JOB_NAME=fm-gen-run1 EXPECTED_MEMORY="$HM1_DIGEST" \
    bash official/vm/run-set-cluster2.sh
  python3 scripts/analyze_arms_cluster2.py --arm "$set_name" --summary "fm-tasks-$set_name" --dir "$ANALYSIS" | tee -a "$LOGF"
done

step "STUDY_DONE"
date > official/vm/DRIVER_DONE_CLUSTER2
