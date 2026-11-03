"""Corpus coverage per task, v1.0 vs v1.1. Counts only: no corpus text is printed or written.

A run matches a task when its first user message holds a share of the words distinctive to that task's instruction.
This is approximate, so several cutoffs are reported. PASS/FAIL comes from the verifier line at the end of the run.
The totals are checked against the published counts.
Usage: python3 -I scripts/corpus_coverage.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from build_corpus_evidence_v5 import Stats, load_items, outcome_of  # noqa: E402

CORPORA = {"v1.0": (REPO / "data/corpus/joint-674-v1.0/inputs", (184, 490)),
           "v1.1": (REPO / "data/corpus/v1.1/inputs", (256, 494))}
TASKS = REPO / "data/tasks/frontier-memory"
TOKEN = re.compile(r"[a-z][a-z0-9_]{3,}")
THRESHOLDS = (0.3, 0.5, 0.7)


def tokens(text: str) -> set[str]:
    return set(TOKEN.findall(text.lower()))


def scan(root: Path, tasks: dict[str, set[str]]) -> dict:
    """A run matches a task when its first user message holds a given share of the task instruction's distinctive tokens."""
    totals, hashes, runs = Counter(), {}, []
    for path in sorted(root.iterdir()):
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        _, items = load_items(path, Stats())
        verdict = outcome_of(items) or "NONE"
        totals[verdict] += 1
        first = next((text for _, role, text in items if role == "user"), "")
        runs.append((verdict, tokens(first)))
    per_task = {}
    for name, want in tasks.items():
        row = {}
        for cut in THRESHOLDS:
            hits = Counter(v for v, have in runs if want and len(want & have) / len(want) >= cut)
            row[str(cut)] = {"PASS": hits["PASS"], "FAIL": hits["FAIL"]}
        per_task[name] = row
    return {"totals": dict(totals), "tasks": per_task, "hashes": hashes,
            "distinct_files": len(set(hashes.values())), "files": len(hashes)}


def distinctive_instruction_tokens() -> dict[str, set[str]]:
    """Tokens of each task's instruction that at most 2 other tasks use, so shared boilerplate doesn't count."""
    raw = {d.name: tokens((d / "instruction.md").read_text(errors="ignore")) for d in sorted(TASKS.iterdir()) if d.is_dir()}
    seen = Counter(t for ts in raw.values() for t in ts)
    return {k: {t for t in v if seen[t] <= 3} for k, v in raw.items()}


def main() -> None:
    tasks = distinctive_instruction_tokens()
    out = {}
    for name, (root, (passed, failed)) in CORPORA.items():
        r = scan(root, tasks)
        ok = r["totals"].get("PASS") == passed and r["totals"].get("FAIL") == failed
        print(name, r["totals"], "matches published" if ok else f"DOES NOT MATCH published {passed}/{failed}",
              f"{r['distinct_files']} distinct of {r['files']} files")
        out[name] = r
    out["v1.0"].pop("hashes"); out["v1.1"].pop("hashes")
    print("runs matching each task, PASS/FAIL, at 30% / 50% / 70% of distinctive instruction tokens")
    for k in tasks:
        cells = []
        for v in CORPORA:
            cells.append("  ".join(f"{out[v]['tasks'][k][str(c)]['PASS']}/{out[v]['tasks'][k][str(c)]['FAIL']}" for c in THRESHOLDS))
        print(f"{k[:44]:44s} tokens={len(tasks[k]):3d} | v1.0 {cells[0]:22s} | v1.1 {cells[1]}")
    (REPO / "results/corpus-coverage.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
