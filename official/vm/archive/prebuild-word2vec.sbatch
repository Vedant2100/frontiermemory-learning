#!/bin/bash
# Fill Docker's layer cache for Word2Vec from the unmodified task, without the 600 s build limit, then rerun its oracle under official limits. Task files unchanged.
#SBATCH --job-name=fm-w2v-build
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu01
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=03:00:00
#SBATCH --output=official/logs/w2v-build-%j.log
source official/vm/lib.sh; vm_boot 6 20G || exit 1
"${SSH[@]}" 'cd ~/official/frontiermemory; T=data/tasks/frontier-memory/build-word2vec-pipeline; S=$(date +%s)
sudo docker build -q -t fm-w2v-cache $T/environment 2>&1 | tail -3 | cut -c1-200; echo "build took $(( $(date +%s)-S )) s"; sudo docker images fm-w2v-cache --format "{{.ID}} {{.Size}}"; sudo docker inspect fm-w2v-cache --format "{{.Id}}"
sudo env PATH=$PWD/.venv/bin:$PATH harbor run -p $(dirname $T) -a oracle -e docker -n 1 -i "build-word2vec*" --jobs-dir jobs --job-name oracle-w2v -y 2>&1 | tail -2 | cut -c1-140; sudo chown -R fm:fm jobs/oracle-w2v
python3 - <<PY
import json
from pathlib import Path
for r in Path("jobs/oracle-w2v").glob("*/result.json"):
    d=json.loads(r.read_text()); e=d.get("exception_info") or {}; print(d.get("task_name"),(d.get("verifier_result") or {}).get("rewards"),e.get("exception_type",""),str(e.get("exception_message",""))[:160])
PY'
