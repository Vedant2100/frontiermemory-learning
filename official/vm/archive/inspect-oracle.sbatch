#!/bin/bash
# Read oracle failures in the guest. Read-only apart from booting the VM. Key-like strings and preference-check lines are filtered.
#SBATCH --job-name=fm-inspect
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu01
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=official/logs/inspect-%j.log
source official/vm/lib.sh; vm_boot 4 6G || exit 1
"${SSH[@]}" 'cd ~/official/frontiermemory; T=data/tasks/frontier-memory/build-word2vec-pipeline; echo "### word2vec env files"; ls $T/environment; grep -nE "^FROM|apt-get|pip install|HEALTHCHECK" $T/environment/Dockerfile | cut -c1-140; sed -n "/^\[environment\]/,/^$/p" $T/task.toml | cut -c1-100
d=$(ls -d jobs/oracle-retest/build-word2vec*__* | head -1); echo "### word2vec trial.log"; sudo tail -25 $d/trial.log | cut -c1-200
echo "### pull/build timing"; sudo docker images | grep -iE "word2vec|hb__" | cut -c1-100 | head; timeout 60 sudo docker pull hello-world 2>&1 | tail -1 | cut -c1-200; F=$(grep -m1 -E "^FROM" $T/environment/Dockerfile | cut -d" " -f2); echo "base: $F"; time (timeout 120 sudo docker pull $F 2>&1 | tail -1 | cut -c1-200)
d=$(ls -d jobs/oracle-retest/cookie-store*__* | head -1); echo "### cookie"; sudo ls $d/verifier; sudo tail -30 $d/verifier/test-stdout.txt | grep -viE "preference" | cut -c1-200; sudo tail -12 $d/trial.log | grep -viE "preference" | cut -c1-220; python3 -c "
import json,sys;e=json.load(open(sys.argv[1])).get(\"exception_info\") or {};print(e.get(\"exception_type\"));print(e.get(\"exception_traceback\",\"\")[-500:])" $d/result.json
free -g | sed -n 2p' 2>&1 | sed -E 's/sk-[A-Za-z0-9_-]{8,}/sk-REDACTED/g'
