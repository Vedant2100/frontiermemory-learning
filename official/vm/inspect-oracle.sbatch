#!/bin/bash
# Read oracle failures in the guest. Read-only apart from booting the VM. Key-like strings are scrubbed.
#SBATCH --job-name=fm-inspect
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu01
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:15:00
#SBATCH --output=official/logs/inspect-%j.log
source official/vm/lib.sh; vm_boot 2 4G || exit 1
"${SSH[@]}" 'cd ~/official/frontiermemory/jobs/oracle-tasks; ls | head -4
for t in awilix-release-tier-implicit customer-delivery build-word2vec; do d=$(ls -d ${t}*__* | head -1); echo "##### $d"; ls $d; python3 -c "
import json,sys;d=json.load(open(sys.argv[1]));e=d.get(\"exception_info\") or {};print(e.get(\"exception_type\"));print(e.get(\"exception_message\",\"\")[:400]);print(e.get(\"exception_traceback\",\"\")[-900:])" $d/result.json; done
for t in apex-eurogrid apex-brightpath-market; do d=$(ls -d ${t}*__* | head -1); echo "##### $d"; find $d/verifier -maxdepth 1 -type f | head; tail -25 $d/verifier/test-stdout.txt 2>/dev/null | cut -c1-220; cat $d/verifier/reward.json 2>/dev/null | cut -c1-300; done
ls -ld ~/official/frontiermemory/jobs/oracle-tasks/*/* | head -4; id; df -h / | tail -1' 2>&1 | sed -E 's/sk-[A-Za-z0-9_-]{8,}/sk-REDACTED/g'
