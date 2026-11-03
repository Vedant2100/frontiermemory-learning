#!/bin/bash
# Verify the gate from saved trials. Prints counts, structure and verifier summaries; no corpus or memory text.
#SBATCH --job-name=fm-inspect
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu02
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:20:00
#SBATCH --output=official/logs/inspect-gate2-%j.log
source official/vm/lib.sh; vm_boot 2 4G || exit 1
"${SSH[@]}" 'cd ~/official/frontiermemory; python3 - <<PY
import json,glob,re,os,tarfile
print("== bundle SUBMISSION.json")
t=tarfile.open("compliant-bundle.tar.gz"); names=t.getnames(); m=[n for n in names if n.endswith("SUBMISSION.json")][0]
s=json.load(t.extractfile(m)); print({k:(v if not isinstance(v,(dict,list)) else (list(v)[:12] if isinstance(v,dict) else len(v))) for k,v in s.items()})
print("corpus",s.get("corpus_sha256"),"memory",s.get("memory_sha256"),"problems",s.get("problems"))
gen=glob.glob("jobs/compliant-gen/*__*")[0]
print("== memory structure (names hidden)")
fs=[f for f in glob.glob(gen+"/artifacts/memory/**",recursive=True) if os.path.isfile(f)]
print(len(fs),"files",sum(os.path.getsize(f) for f in fs),"bytes; MEMORY.md bytes",os.path.getsize(gen+"/artifacts/memory/MEMORY.md"),"SKILL.md count",sum(f.endswith("SKILL.md") for f in fs))
txt=" ".join(open(f,errors="ignore").read() for f in fs).lower()
for k in ("word2vec","gensim","nltk","task_func","solution.py","pcap","awilix","cattrs","cookie","brightpath","eurogrid"):
    print(k,txt.count(k),end="; ")
print()
print("== trials")
for j in ("compliant2-w2v-nomem","compliant2-w2v-mem"):
  for d in sorted(glob.glob("jobs/"+j+"/*__*")):
    r=json.load(open(d+"/result.json")); a=r.get("agent_result") or {}; md=a.get("metadata") or {}
    fm=md.get("frontier_memory"); print(j[-8:],d[-7:],"fm_keys",(list(fm)[:8] if isinstance(fm,dict) else fm),"digest",(fm or {}).get("sha256",(fm or {}).get("digest")) if isinstance(fm,dict) else None)
    sj=d+"/agent/hermes-session.jsonl"; 
    if os.path.exists(sj):
        ss=[json.loads(l) for l in open(sj) if l.strip()]; x=ss[0]; sp=x.get("system_prompt") or ""
        msgs=x.get("messages") or []
        tools=[]
        for m in msgs:
            for c in (m.get("tool_calls") or []):
                tools.append((c.get("function") or {}).get("name") or c.get("name"))
        import collections
        blob=json.dumps(msgs).lower()
        print("  sys_prompt chars",len(sp),"memory block",("MEMORY" in sp),"sessions",len(ss),"tool_calls",dict(collections.Counter(tools)),"hermes/memories in msgs",blob.count("/tmp/hermes/memories"),"skill refs",blob.count("skill_view"),"word2vec in sys",sp.lower().count("word2vec"),"end",x.get("end_reason"))
    cfg=d+"/agent/hermes-config.yaml"
    if os.path.exists(cfg): print("  cfg",[l.strip() for l in open(cfg) if re.search("memory_enabled|user_profile|disabled_toolsets|reasoning_effort",l)])
    v=d+"/verifier/test-stdout.txt"
    if os.path.exists(v):
        o=open(v,errors="ignore").read(); print("  verifier:",[l[:110] for l in o.splitlines() if re.search(r"(passed|failed|error)( |,|$)|FAILED|ERROR",l)][-5:])
    print("  solution exists",os.path.exists(d+"/artifacts/workspace/solution.py"), os.path.getsize(d+"/artifacts/workspace/solution.py") if os.path.exists(d+"/artifacts/workspace/solution.py") else None)
PY
sudo docker images --format "{{.Size}} {{.Repository}}" | cut -c1-60 | head -5; sudo docker ps -a --format "{{.Names}} {{.Status}}" | wc -l; df -h / | tail -1' 2>&1 | sed -E 's/sk-[A-Za-z0-9_-]{8,}/sk-REDACTED/g'
