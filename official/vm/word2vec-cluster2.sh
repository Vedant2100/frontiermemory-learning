#!/bin/bash
set -euo pipefail
source official/vm/lib-cluster2.sh
vm_boot 6 20G
ENV='cd ~/official/frontiermemory && . .venv/bin/activate'
step "Word2Vec image from the unmodified task (D71)"
G 'cd ~/official/frontiermemory; S=$(date +%s); sudo docker build -q -t fm-w2v-cache data/tasks/frontier-memory/build-word2vec-pipeline/environment 2>&1 | tail -1 | cut -c1-90; echo "build took $(( $(date +%s)-S )) s"; sudo docker images fm-w2v-cache --format "{{.ID}} {{.Size}}"; df -h / | tail -1'
G 'for i in 1 2 3 4 5 6; do sudo docker pull -q '"$PROBE_IMAGE"' && break; sleep 20; done'
step "reference solution on Word2Vec"
G "$ENV; sudo env PATH=\$PATH harbor run -p data/tasks-fm -a oracle -e docker -n 1 -i 'build-word2vec*' --jobs-dir jobs --job-name oracle-w2v -y 2>&1 | tail -1 | cut -c1-100; sudo chown -R fm:fm jobs; python3 -c \"
import json,glob
for r in glob.glob('jobs/oracle-w2v/*/result.json'):
    d=json.load(open(r)); print((d.get('verifier_result') or {}).get('rewards'),(d.get('exception_info') or {}).get('exception_type',''))\""
