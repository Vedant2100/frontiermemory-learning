#!/bin/bash
# Reference solutions on all 15 tasks in this exact guest, from the repaired task copy, with the Claude judge. Caches every image before counted trials. CPU only.
#SBATCH --job-name=fm-oracle-all
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu02
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=06:00:00
#SBATCH --output=official/logs/oracle-all-%j.log
source official/vm/lib.sh; vm_boot 7 28G || exit 1
"${SSH[@]}" 'sudo docker ps -aq | xargs -r sudo docker rm -f >/dev/null 2>&1; sudo docker network prune -f >/dev/null 2>&1; rm -f ~/.judge-key ~/key-audit-gate.log; for i in 1 2 3 4 5 6; do sudo docker pull -q '"$PROBE_IMAGE"' >/dev/null && break; sleep 20; done'
"${SSH[@]}" 'umask 077; cat > ~/.judge-key' < "$HOME/.config/frontiermemory/anthropic-api-key"
"${SSH[@]}" 'cd ~/official/frontiermemory; export PATH=$PWD/.venv/bin:$PATH JUDGE_ANTHROPIC_KEY=$(cat ~/.judge-key); sudo env PATH=$PATH JUDGE_ANTHROPIC_KEY=$JUDGE_ANTHROPIC_KEY harbor run -p data/tasks-fm -a oracle -e docker -n 2 --ve GRADING_MODEL=anthropic/claude-opus-5-5 --ve "ANTHROPIC_API_KEY=\${JUDGE_ANTHROPIC_KEY}" --jobs-dir jobs --job-name oracle-all -y 2>&1 | tail -1 | cut -c1-120; sudo chown -R fm:fm jobs/oracle-all; rm -f ~/.judge-key
python3 - <<PY
import json,glob
want={"apex-brightpath-market-share":1,"apex-brightpath-seat-surplus":1,"apex-eurogrid-curtailment":0.8333,"automationbench-marketing-content-gap-analysis":1,"automationbench-sales-chatgpt-proposal-customization":1,"automationbench-sales-partnership-contract":1,"awilix-release-tier-explicit":1,"awilix-release-tier-implicit":1,"build-word2vec-pipeline":1,"cattrs-compositional-changelog":0,"cookie-store-compositional-changelog":0,"customer-delivery-contextual-preferences":1,"dapt-intrusion-detection-workflow-learning":1,"enterpriseops-csm-26d1b04a":0,"enterpriseops-teams-2725d17f":0}
got={}
for p in glob.glob("jobs/oracle-all/*__*/result.json"):
    d=json.load(open(p)); t=d["task_name"].split("/")[-1]; got[t]=((d.get("verifier_result") or {}).get("rewards") or {}).get("reward"),(d.get("exception_info") or {}).get("exception_type","")
bad=0
for t,w in want.items():
    g=got.get(t,(None,"missing")); ok=g[0] is not None and abs(g[0]-w)<0.01; bad+=not ok; print("OK " if ok else "BAD",t,"want",w,"got",g[0],g[1])
print("ORACLE_MATCHES" if bad==0 else f"ORACLE_MISMATCH {bad}")
PY
sudo docker images --format "{{.Repository}}" | grep -c .; sudo docker system df | cut -c1-70; df -h / | tail -1' 2>&1 | sed -E 's/sk-[A-Za-z0-9_-]{8,}/sk-REDACTED/g'
