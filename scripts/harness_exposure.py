"""Simulate how much of a MEMORY.md each task harness puts in the model's context.

Rules (sources in results/harness-exposure-survey.md): Codex 2,500 tokens x 4 bytes, head+tail;
Claude Code first 200 lines or 25 KB; OpenAI Agents SDK 15,000 tokens x 4 bytes, head+tail;
Hermes whole file. Prints counts only; topic slugs are memory content.

Usage: python3 scripts/harness_exposure.py memory/frozen-v5-fullindex memory/frozen-r25
"""
import re,sys
SLUG=re.compile(r"g\d{3}-[a-z0-9-]+")
def headtail(b,budget):
    if len(b)<=budget: return b
    h=budget//2; return b[:h]+b"\n"+b[-(budget-h):]
def claude(b):
    lines=b.split(b"\n")[:200]; t=b"\n".join(lines); return t[:25*1024]
rules={"Codex CLI (2,500 tok ~ 10 KB, head+tail)":lambda b:headtail(b,2500*4),
       "Claude Code (first 200 lines or 25 KB)":claude,
       "OpenAI Agents SDK (15,000 tok ~ 60 KB, head+tail)":lambda b:headtail(b,15000*4),
       "Hermes (whole MEMORY.md)":lambda b:b}
for m in sys.argv[1:]:
    b=open(m+"/MEMORY.md","rb").read(); allt=set(SLUG.findall(b.decode("utf-8","ignore")))
    print(f"== {m}: {len(b)} bytes, {len(allt)} topics in index")
    for k,f in rules.items():
        v=f(b); s=set(SLUG.findall(v.decode("utf-8","ignore")))&allt
        w2v=sorted(x for x in allt if "word2vec" in x or "w2v" in x); vw=[x for x in w2v if x in s]
        print(f"  {k:52s} shown {len(v):6d} B ({100*len(v)/len(b):5.1f}%)  topics {len(s):3d}/{len(allt)}  word2vec topics {len(vw)}/{len(w2v)}")
