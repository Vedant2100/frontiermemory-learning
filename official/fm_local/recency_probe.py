"""Score a generated memory against the recency arm's injected facts (build_recency_corpus.py). No model, no task trials.

For each injected fact: is the current canary in the memory, the stale one, both, or neither. The canaries are synthetic,
so printing them reveals nothing from the corpus.

    python3 recency_probe.py <memory folder or generation job> <out root>.facts.json
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_placebo import resolve  # noqa: E402


def probe(memory: Path, facts: dict) -> dict:
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in sorted(memory.rglob("*")) if p.is_file())
    rows = {}
    for fact, f in sorted(facts.items()):
        cur, old = f["current"] in text, f["stale"] in text
        rows[fact] = "both" if cur and old else "current_only" if cur else "stale_only" if old else "neither"
    return {"facts": len(rows), "outcomes": dict(Counter(rows.values())), "by_fact": rows}


def main(argv: list[str]) -> int:
    memory = resolve(Path(argv[1]))
    report = json.loads(Path(argv[2]).read_text())
    result = {"variant": report["variant"], **probe(memory, report["facts"])}
    print("RECENCY_PROBE", json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
