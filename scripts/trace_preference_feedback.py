#!/usr/bin/env python3
"""Trace curated user-feedback messages from corpus v1.0 into evidence, notes, topic files and the visible window. Counts only."""
import json,glob,os,re,math,collections,sys
sys.path.insert(0,"scripts")
from memory_exposure import visible
C="data/corpus/joint-674-v1.0/inputs/"; G="results/memory-generation-v5/"
TOK=re.compile(r"[A-Za-z_][A-Za-z0-9_.\-/]{3,}")
def toks(s): return {t.lower().strip(".-/") for t in TOK.findall(s)}
evid={os.path.basename(p)[:-4]:open(p,errors="ignore").read() for p in glob.glob(G+"evidence/*.txt")}
df=collections.Counter()
for t in evid.values(): df.update(toks(t))
N=len(evid)
fb=[]
for p in sorted(glob.glob(C+"*.jsonl")):
    for l in open(p,errors="ignore"):
        if "dreambench-user-feedback" not in l: continue
        r=json.loads(l)
        if "user-feedback" in json.dumps(r.get("metadata",{})):
            fb.append((os.path.basename(p)[:-6],r["text"]))
def distinctive(text,k=8):
    ts=[t for t in toks(text) if 1<=df[t]<=max(2,int(0.03*N))]
    return sorted(ts,key=lambda t:(df[t],t))[:k]
mem={"M3":"memory/frozen-v5-fullindex","R25":"memory/frozen-r25"}
memtxt={a:" ".join(open(f,errors="ignore").read() for f in glob.glob(d+"/topics/*.md")).lower() for a,d in mem.items()}
vis={a:visible(open(d+"/MEMORY.md").read()).lower() for a,d in mem.items()}
groups=json.load(open(G+"groups.json"))["groups"]
gid={i:g["slug"] for g in groups for i in g["ids"]}
r25ids=set(i for g in json.load(open("results/memory-generation-r25/groups.json"))["groups"] for i in g["ids"])
out=collections.Counter(); per=[]
for tid,text in fb:
    d=distinctive(text)
    note=open(G+f"notes/{tid}.json",errors="ignore").read().lower() if os.path.exists(G+f"notes/{tid}.json") else ""
    topic=open(f"memory/frozen-v5-fullindex/topics/{gid[tid]}.md",errors="ignore").read().lower() if tid in gid and os.path.exists(f"memory/frozen-v5-fullindex/topics/{gid[tid]}.md") else ""
    def rec(s): return sum(t in s for t in d)/len(d) if d else float("nan")
    row=dict(tid=tid,n_dist=len(d),note=rec(note),topic=rec(topic),m3_any=rec(memtxt["M3"]),m3_vis=rec(vis["M3"]),in_r25=tid in r25ids,r25_any=rec(memtxt["R25"]),r25_vis=rec(vis["R25"]))
    per.append(row)
def summ(key,cond=lambda r:True):
    v=[r[key] for r in per if cond(r) and r["n_dist"]>0]
    return dict(n=len(v),mean=round(sum(v)/len(v),2) if v else None,ge50=sum(x>=0.5 for x in v),zero=sum(x==0 for x in v))
print("feedback messages:",len(fb),"runs:",len({t for t,_ in fb}),"with distinctive tokens:",sum(r['n_dist']>0 for r in per))
for k in ["note","topic","m3_any","m3_vis"]: print(k,summ(k))
print("in R25 sample:",sum(r["in_r25"] for r in per))
for k in ["r25_any","r25_vis"]: print(k,summ(k,lambda r:r["in_r25"]))
if len(sys.argv)>1: json.dump(per,open(sys.argv[1],"w"),indent=1)

fams=collections.Counter(next((g["label"] for g in groups if t in g["ids"]),"?") for t,_ in fb)
print("feedback runs: groups",len(fams),"largest group share",max(fams.values()),"/",len(fb))
