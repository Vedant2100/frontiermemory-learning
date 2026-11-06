"""Recency arm: a copy of the corpus with one superseded fact per task family (results/preregistration-arms.md).

Design after MemoryAgentBench's FactConsolidation (Hu, Wang & McAuley, arXiv 2507.05257: an original fact and a rewritten
one, scored directly) and LongMemEval's knowledge-update questions (Wu et al., ICLR 2025): among each task family's
relevant runs (fm_local/evidence-runs.json, from results/recency-check.json) that are timed ATIF trajectories, the k-th earliest run gets a stale value and
the k-th latest the current value of synthetic preference k (up to PAIRS_PER_FAMILY per family), as one user step
appended after the run's last step, with the same wording. Nothing says which value replaces which; only the runs' own
timestamps do.
Variant a: the corpus as released, so the later run is wherever its file sorts. Variant b: the two host files swap names,
so the read order of the pair flips while the timestamps do not. Comparing a and b separates "keeps the newer" from
"keeps whichever it read last". The values are synthetic canaries, so recency_probe.py can score the generated memory
directly, without task trials: task verifiers do not test these facts.

    python3 build_recency_corpus.py <corpus root> <evidence-runs.json> <out root> a|b
Writes <out root> (inputs/ + SHA256SUMS, the layout frontier_memory.corpus verifies) and <out root>.facts.json.
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import sys
from pathlib import Path

# Task families, as scripts/recency_check.py FAMILIES (a host test checks they match).
FAMILIES = ("apex-brightpath", "apex-eurogrid", "automationbench", "awilix", "build-word2vec", "cattrs", "cookie-store",
            "customer-delivery", "dapt", "enterpriseops")
TEMPLATES = (  # one independent synthetic preference per pair index; stale and current use the same wording
    "User feedback for future {family} work: name the final report or summary file with the prefix {value}, "
    "for example {value}-summary.md.",
    "User feedback for future {family} work: put the tag {value} on the first line of any notes file you write.",
    "User feedback for future {family} work: call any scratch directory you create {value}-scratch.",
)
PAIRS_PER_FAMILY = len(TEMPLATES)


def canary(fact: str, role: str) -> str:
    return "FM" + base64.b32encode(hashlib.sha256(f"recency-v1|{fact}|{role}".encode()).digest()).decode()[:6]


def atif_time(path: Path) -> str | None:
    """Earliest step timestamp of an ATIF trajectory file, or None if it is not one with timed steps."""
    if path.suffix != ".json":
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    steps = doc.get("steps") if isinstance(doc, dict) else None
    if not steps or not all(isinstance(s, dict) and isinstance(s.get("timestamp"), str) for s in steps):
        return None
    return min(s["timestamp"] for s in steps)


def choose_hosts(inputs: Path, relevance: dict[str, list[str]]) -> dict[str, tuple[str, str]]:
    """fact id "<family>#<k>" -> (stale host file, current host file): the k-th earliest and k-th latest timed ATIF run
    of the family, k < PAIRS_PER_FAMILY, stale strictly older than current; every file hosts at most one fact.
    relevance: {task: [corpus file names]} (fm_local/evidence-runs.json)."""
    runs: dict[str, set[str]] = {}
    for task, names in relevance.items():
        fam = next((f for f in FAMILIES if task.startswith(f)), None)
        if fam:
            runs.setdefault(fam, set()).update(names)
    used, hosts = set(), {}
    for fam in sorted(runs):
        timed = sorted((t, n) for n in runs[fam] if (inputs / n).is_file() and n not in used
                       and (t := atif_time(inputs / n)) is not None)
        for k in range(min(PAIRS_PER_FAMILY, len(timed) // 2)):
            old, new = timed[k], timed[-1 - k]
            if old[0] < new[0]:
                hosts[f"{fam}#{k}"] = (old[1], new[1])
                used.update((old[1], new[1]))
    return hosts


def inject(path: Path, message: str) -> bytes:
    doc = json.loads(path.read_text(encoding="utf-8"))
    last = doc["steps"][-1]
    step_id = max((s.get("step_id") or 0) for s in doc["steps"] if isinstance(s.get("step_id"), int)) + 1
    doc["steps"].append({"step_id": step_id, "source": "user", "message": message, "timestamp": last["timestamp"]})
    return (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def build(corpus: Path, relevance: dict, out: Path, variant: str) -> dict:
    if variant not in ("a", "b"):
        raise ValueError("variant must be a or b")
    if out.exists():
        raise ValueError(f"{out} already exists")
    inputs = corpus / "inputs"
    hosts = choose_hosts(inputs, relevance)
    rename = {}
    if variant == "b":
        for stale, current in hosts.values():
            rename[stale], rename[current] = current, stale
    content = {}
    facts = {}
    for fact, (stale, current) in hosts.items():
        fam, k = fact.split("#")
        facts[fact] = {"stale": canary(fact, "stale"), "current": canary(fact, "current"),
                       "stale_host": Path(stale).stem, "current_host": Path(current).stem}
        template = TEMPLATES[int(k)]
        content[stale] = inject(inputs / stale, template.format(family=fam, value=facts[fact]["stale"]))
        content[current] = inject(inputs / current, template.format(family=fam, value=facts[fact]["current"]))
    (out / "inputs").mkdir(parents=True)
    sums = []
    for p in sorted(inputs.iterdir()):
        name = rename.get(p.name, p.name)
        dest = out / "inputs" / name
        if p.name in content:
            dest.write_bytes(content[p.name])
        else:
            shutil.copyfile(p, dest)
    for p in sorted((out / "inputs").iterdir()):
        sums.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  inputs/{p.name}\n")
    (out / "SHA256SUMS").write_text("".join(sums))
    report = {"variant": variant, "facts_count": len(facts), "families": len({f.split("#")[0] for f in facts}),
              "facts": facts, "corpus_sha256": hashlib.sha256((out / "SHA256SUMS").read_bytes()).hexdigest(),
              "files": len(sums), "files_source": sum(1 for p in inputs.iterdir() if p.is_file())}
    report["ok"] = report["files"] == report["files_source"] and report["facts_count"] >= 6
    return report


def main(argv: list[str]) -> int:
    corpus, relevance, out, variant = Path(argv[1]), json.loads(Path(argv[2]).read_text()), Path(argv[3]), argv[4]
    report = build(corpus, relevance, out, variant)
    Path(str(out) + ".facts.json").write_text(json.dumps(report, indent=1) + "\n")
    print("RECENCY_CORPUS", json.dumps({k: v for k, v in report.items() if k != "facts"}, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
