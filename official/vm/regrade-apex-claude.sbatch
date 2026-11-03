#!/bin/bash
# Regrade saved APEX oracle trials with a Claude judge. Tests harbor trials regrade and the judge together. No agent runs. Key goes to the verifier only.
#SBATCH --job-name=fm-regrade
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu01
#SBATCH --cpus-per-task=5
#SBATCH --mem=16G
#SBATCH --time=01:30:00
#SBATCH --output=official/logs/regrade-%j.log
source official/vm/lib.sh; vm_boot 4 12G || exit 1
"${SSH[@]}" 'umask 077; cat > ~/.judge-key' < "$HOME/.config/frontiermemory/anthropic-api-key"
"${SSH[@]}" 'cd ~/official/frontiermemory; export PATH=$PWD/.venv/bin:$PATH JUDGE_ANTHROPIC_KEY=$(cat ~/.judge-key); sudo chown -R fm:fm jobs/oracle-tasks 2>/dev/null
for t in apex-brightpath-market-share apex-brightpath-seat-surplus apex-eurogrid-curtailment; do
  s=$(ls -d jobs/oracle-tasks/$t*__* | head -1); echo "### $t"
  sudo -E env PATH=$PATH harbor trials regrade "$s" -p data/tasks-fm/$t -e docker --ve GRADING_MODEL=anthropic/claude-opus-5-5 --ve "ANTHROPIC_API_KEY=${JUDGE_ANTHROPIC_KEY}" --trial-name regrade-$t -o jobs/regrade-claude 2>&1 | tail -3 | cut -c1-170
  sudo chown -R fm:fm jobs/regrade-claude
  d=jobs/regrade-claude/regrade-$t; python3 -c "
import json,sys;d=json.load(open(sys.argv[1]));e=d.get(\"exception_info\") or {};print(\"reward\",(d.get(\"verifier_result\") or {}).get(\"rewards\"),e.get(\"exception_type\",\"\"),str(e.get(\"exception_message\",\"\"))[:220])" $d/result.json
  grep -E "\[GRADING\]\[END\]|AuthenticationError|BadRequest|NotFoundError" $d/verifier/grade_log.txt 2>/dev/null | cut -c1-260 | sort -u | head -4
  python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print({k:(v if not isinstance(v,(list,dict)) else len(v)) for k,v in d.items()} if isinstance(d,dict) else type(d))" $d/verifier/grade_details.json 2>/dev/null | cut -c1-260
done
echo "### key not stored in configs:"; sudo grep -rlF "$JUDGE_ANTHROPIC_KEY" jobs/regrade-claude 2>/dev/null | wc -l; rm -f ~/.judge-key' 2>&1 | sed -E 's/sk-[A-Za-z0-9_-]{8,}/sk-REDACTED/g'
