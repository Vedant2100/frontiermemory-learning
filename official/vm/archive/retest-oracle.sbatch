#!/bin/bash
# Retest the oracle on tasks that hit infrastructure errors, with Harbor as root in the guest so it can read files containers create. No judge key needed.
#SBATCH --job-name=fm-oracle2
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu01
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=06:00:00
#SBATCH --output=official/logs/oracle2-%j.log
source official/vm/lib.sh; vm_boot 6 24G || exit 1
"${SSH[@]}" 'cd ~/official/frontiermemory; T=$(dirname $(dirname $(find data/tasks -name task.toml | head -1)))
sudo env PATH=$PWD/.venv/bin:$PATH harbor run -p $T -a oracle -e docker -n 2 \
  --include-task-name "awilix*" --include-task-name "customer*" --include-task-name "cattrs*" --include-task-name "cookie*" --include-task-name "build-word2vec*" \
  --ve GRADING_MODEL=openai/gpt-5.6-sol --jobs-dir jobs --job-name oracle-retest -y 2>&1 | tail -3 | cut -c1-160
sudo chown -R fm:fm jobs/oracle-retest
python3 - <<PY
import json
from pathlib import Path
for r in sorted(Path("jobs/oracle-retest").glob("*/result.json")):
    d=json.loads(r.read_text()); v=(d.get("verifier_result") or {}).get("rewards") or {}; e=d.get("exception_info") or {}
    print(d.get("task_name"), v.get("reward"), e.get("exception_type",""), str(e.get("exception_message",""))[:160])
print("--- memory task oracle")
for r in Path("jobs/oracle-memory").glob("*/result.json"):
    d=json.loads(r.read_text()); print((d.get("verifier_result") or {}).get("rewards"), (d.get("exception_info") or {}).get("exception_type",""))
PY
df -h / | tail -1'
