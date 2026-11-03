#!/bin/bash
# Read gate results in the guest. Prints errors, counts and config only, never corpus text.
#SBATCH --job-name=fm-inspect
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu02
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:15:00
#SBATCH --output=official/logs/inspect-gate-%j.log
source official/vm/lib.sh; vm_boot 2 4G || exit 1
"${SSH[@]}" 'cd ~/official/frontiermemory/jobs; sudo chown -R fm:fm . ; ls gate-gen-short 2>&1 | head; d=$(ls -d gate-gen-short/*__* 2>/dev/null | head -1); echo "trial=$d"; ls $d $d/agent 2>/dev/null | head -30
python3 - "$d" <<PY
import json,sys,glob,os
d=sys.argv[1]
if os.path.exists(d+"/result.json"):
    r=json.load(open(d+"/result.json")); e=r.get("exception_info") or {}
    print("exception",e.get("exception_type"),str(e.get("exception_message"))[:300]); print(str(e.get("exception_traceback"))[-400:])
    print("timing",{k:(r.get(k) or {}).get("started_at","")[11:19]+"-"+(r.get(k) or {}).get("finished_at","")[11:19] for k in ("environment_setup","agent_setup","agent_execution","verifier")})
    print("verifier",r.get("verifier_result"))
p=d+"/agent/hermes-result.json"
if os.path.exists(p):
    h=json.load(open(p)); print({k:(v if not isinstance(v,(list,dict,str)) or k=="usage" else f"<{type(v).__name__} {len(v)}>") for k,v in h.items()})
PY
sed -n "1,4p" $d/config.json 2>/dev/null | cut -c1-120; grep -hiE "error|exception|timeout|timed out|learn|reasoning" $d/trial.log 2>/dev/null | cut -c1-180 | sort | uniq -c | sort -rn | head -12
ls -la $d/agent 2>/dev/null | head -14 | cut -c1-90; echo "--- memory on disk"; find $d -path "*artifacts*" -maxdepth 4 | head -8
echo "--- hermes config sent to model"; find gate-w2v-nomem -name hermes-config.yaml -exec grep -nE "effort|provider|model|context|compress" {} \; | cut -c1-100 | head -12; d2=$(ls -d gate-w2v-nomem/*__* | head -1); grep -iE "reasoning|effort|context|compress" $d2/agent/hermes.txt | cut -c1-160 | head -6; python3 -c "
import json;s=[json.loads(l) for l in open(\"$d2/agent/hermes-session.jsonl\")];print(len(s),[k for k in s[0]][:20]);x=s[0];print({k:x.get(k) for k in (\"model\",\"message_count\",\"tool_call_count\",\"input_tokens\",\"output_tokens\",\"reasoning_tokens\",\"estimated_cost_usd\",\"end_reason\")})" 2>&1 | cut -c1-400' 2>&1 | sed -E 's/sk-[A-Za-z0-9_-]{8,}/sk-REDACTED/g'
