#!/bin/bash
# User decision A (D72): copy the official tasks, add anyio==4.15.1 to cookie-store's verifier wheelhouse, rerun its oracle. Official data/tasks stays untouched.
#SBATCH --job-name=fm-cookie-pin
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu01
#SBATCH --cpus-per-task=5
#SBATCH --mem=20G
#SBATCH --time=02:00:00
#SBATCH --output=official/logs/cookie-pin-%j.log
source official/vm/lib.sh; vm_boot 4 16G || exit 1
"${SSH[@]}" 'cd ~/official/frontiermemory; rm -rf data/tasks-fm; cp -r data/tasks/frontier-memory data/tasks-fm
python3 - <<PY
from pathlib import Path
p=Path("data/tasks-fm/cookie-store-compositional-changelog/tests/Dockerfile"); s=p.read_text()
a="        click==8.1.8 \\\\\n        socksio==1.0.0"
assert s.count(a)==1, "Dockerfile changed"
p.write_text(s.replace(a,"        click==8.1.8 \\\\\n        anyio==4.15.1 \\\\\n        socksio==1.0.0"))
PY
diff -r data/tasks/frontier-memory data/tasks-fm
sudo env PATH=$PWD/.venv/bin:$PATH harbor run -p data/tasks-fm -a oracle -e docker -n 1 -i "cookie*" --ve GRADING_MODEL=openai/gpt-5.6-sol --jobs-dir jobs --job-name oracle-cookie -y 2>&1 | tail -2 | cut -c1-140; sudo chown -R fm:fm jobs/oracle-cookie
d=$(ls -d jobs/oracle-cookie/cookie*__* | head -1); python3 -c "
import json,sys;d=json.load(open(sys.argv[1]));e=d.get(\"exception_info\") or {};print((d.get(\"verifier_result\") or {}).get(\"rewards\"),e.get(\"exception_type\",\"\"),str(e.get(\"exception_message\",\"\"))[:200])" $d/result.json
grep -E " passed| failed|\[verifier\] (functional|New tests|Base tests)|failed to install" $d/verifier/test-stdout.txt | grep -vi preference | cut -c1-140 | tail -8; df -h / | tail -1'
