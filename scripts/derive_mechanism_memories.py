"""Build the mechanism-probe memories of amendments A6 and A7 from frozen M3.

All three are deterministic functions of M3 (digest 4a2eb528...). Each is written read-only to
memory/frozen-m3-<s|w|d>/ and never overwritten. Prints counts and digests only: topic names and
text are memory content and stay local.

  M3S (A6, search only)   adds memory_summary.md = one fixed line, so Codex injects no topic content.
  M3W (A6, minus Word2Vec) drops every topic whose name or text contains "word2vec" and every
                           MEMORY.md line that does (case-insensitive).
  M3D (A7, DAPT shown)    adds memory_summary.md = the one topic matching DAPT_RULE, byte for byte,
                           which fits whole inside Codex's 2,500-token (~10,000-byte) window.

Usage: python3 -I scripts/derive_mechanism_memories.py [--check]
  --check  build into a temporary folder twice, compare digests, write nothing to memory/.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import stat
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "frontiermemory" / "src"))
from frontier_memory.memory import check_memory  # noqa: E402

M3_DIR = REPO / "memory" / "frozen-v5-fullindex"
M3_DIGEST = "4a2eb5286366d650260af0b873a91be9f99b2891a327f0ae73ba8c2e8ef0517a"
SEARCH_ONLY_LINE = "Index of past-run notes: MEMORY.md in this folder; topic files are in topics/.\n"
WORD2VEC_RULE = re.compile(r"word2vec", re.I)
DAPT_RULE = re.compile(r"\bdapt\b|pcap|intrusion|network_stats", re.I)
CODEX_WINDOW_BYTES = 2_500 * 4  # MEMORY_TOOL_DEVELOPER_INSTRUCTIONS_SUMMARY_TOKEN_LIMIT x 4 bytes/token


def digest(root: Path) -> str:
    report = check_memory(root)
    if not report["ok"]:
        raise SystemExit(f"{root.name}: invalid memory: {report['errors']}")
    return report["memory_sha256"]


def topics(root: Path) -> list[Path]:
    return sorted((root / "topics").glob("*.md"))


def build_search_only(out: Path) -> dict:
    (out / "memory_summary.md").write_text(SEARCH_ONLY_LINE, encoding="utf-8")
    return {"summary_bytes": len(SEARCH_ONLY_LINE.encode())}


def build_minus_word2vec(out: Path) -> dict:
    dropped = [t for t in topics(out) if WORD2VEC_RULE.search(t.name) or WORD2VEC_RULE.search(t.read_text("utf-8"))]
    for t in dropped:
        t.unlink()
    index = out / "MEMORY.md"
    lines = index.read_text("utf-8").splitlines(keepends=True)
    kept = [line for line in lines if not WORD2VEC_RULE.search(line)]
    index.write_text("".join(kept), encoding="utf-8")
    left = [t for t in topics(out) if WORD2VEC_RULE.search(t.read_text("utf-8"))]
    assert not left and not WORD2VEC_RULE.search(index.read_text("utf-8")), "word2vec content left"
    return {"topics_dropped": len(dropped), "index_lines_dropped": len(lines) - len(kept)}


def build_dapt_shown(out: Path) -> dict:
    matches = [t for t in topics(out) if DAPT_RULE.search(t.name) or DAPT_RULE.search(t.read_text("utf-8"))]
    if len(matches) != 1:
        raise SystemExit(f"M3D: expected exactly 1 DAPT topic, found {len(matches)}")
    data = matches[0].read_bytes()
    if len(data) > CODEX_WINDOW_BYTES:
        raise SystemExit(f"M3D: topic is {len(data)} bytes, over the {CODEX_WINDOW_BYTES}-byte window")
    (out / "memory_summary.md").write_bytes(data)
    return {"summary_bytes": len(data)}


ARMS = {"M3S": ("frozen-m3-s", build_search_only),
        "M3W": ("frozen-m3-w", build_minus_word2vec),
        "M3D": ("frozen-m3-d", build_dapt_shown)}


def build(dest_root: Path) -> dict:
    if digest(M3_DIR) != M3_DIGEST:
        raise SystemExit("M3 does not match its frozen digest; refusing to derive")
    result = {}
    for arm, (folder, fn) in ARMS.items():
        out = dest_root / folder
        if out.exists():
            raise SystemExit(f"{out} exists; frozen memories are never overwritten")
        shutil.copytree(M3_DIR, out)
        for p in [out, *out.rglob("*")]:
            p.chmod(p.stat().st_mode | stat.S_IWUSR)
        info = fn(out)
        info.update(folder=folder, memory_sha256=digest(out), topic_files=len(topics(out)))
        result[arm] = info
    return result


def freeze(root: Path) -> None:
    for p in sorted(root.rglob("*"), reverse=True):
        p.chmod(p.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    root.chmod(root.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="build twice in a temp folder and compare digests")
    args = ap.parse_args()
    if args.check:
        runs = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as tmp:
                runs.append(build(Path(tmp)))
        same = all(runs[0][a]["memory_sha256"] == runs[1][a]["memory_sha256"] for a in ARMS)
        print(json.dumps({"deterministic": same, "arms": runs[0]}, indent=1))
        sys.exit(0 if same else 1)
    result = build(REPO / "memory")
    for arm, (folder, _) in ARMS.items():
        freeze(REPO / "memory" / folder)
    result = {"source": {"folder": M3_DIR.name, "memory_sha256": M3_DIGEST}, "arms": result}
    out = REPO / "results" / "mechanism-memories.json"
    out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
