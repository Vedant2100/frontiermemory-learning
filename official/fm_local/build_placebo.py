"""Placebo arm: a memory with the shape of a real one and none of its content (results/preregistration-arms.md).

Same number of skills and files, each file the same number of bytes, a valid Hermes /learn MEMORY.md index; neutral names
(skills/note-NN/SKILL.md, part-NN.md, notes/part-NN.md) and text taken in order from placebo_source.txt (Moby-Dick,
Project Gutenberg eBook #2701, public domain; header and licence removed, ASCII-normalised, first ~400 KB). So the task
agent sees a memory-shaped prompt of the same size with irrelevant content, which separates "this content helps" from
"any memory-shaped context of this size changes behaviour" (Du et al., Findings of EMNLP 2025, arXiv 2510.05381).

    python3 build_placebo.py <memory folder or generation job> <out folder> [source text]
Prints and writes <out>/../<out name>.placebo-report.json: counts and digests only, never memory text or file names.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import arm_logic  # noqa: E402

SOURCE = Path(__file__).with_name("placebo_source.txt")
INDEX_HEAD = "# Learned Hermes skills\n\n"  # hermes_dream.export_skills's format


def resolve(path: Path) -> Path:
    if (path / "MEMORY.md").is_file():
        return path
    from frontier_memory.cli import resolve_memory  # a generation job folder; only in the guest's venv
    return resolve_memory(path)


class Filler:
    def __init__(self, text: str):
        if not text.isascii() or not text:
            raise ValueError("placebo source must be non-empty ASCII, so byte counts can be matched exactly")
        self.text, self.pos, self.wraps = text, 0, 0

    def take(self, n: int) -> str:
        out = []
        while n > 0:
            if self.pos >= len(self.text):
                self.pos, self.wraps = 0, self.wraps + 1
            chunk = self.text[self.pos:self.pos + n]
            out.append(chunk)
            self.pos += len(chunk)
            n -= len(chunk)
        return "".join(out)


def plan(memory: Path) -> list[tuple[str, str, int]]:
    """(source rel, placebo rel, bytes) for every file, in a fixed order. MEMORY.md first."""
    root = memory / "skills"
    rels = [s["rel"] for s in arm_logic.skills(memory)]
    owned, rows = set(), [("MEMORY.md", "MEMORY.md", (memory / "MEMORY.md").stat().st_size)]
    for i, rel in enumerate(rels, 1):
        part = 0
        for p in arm_logic.skill_files(root, rel, rels):
            src = p.relative_to(memory).as_posix()
            owned.add(src)
            if p.name == "SKILL.md" and p.parent == root / rel:
                dst = f"skills/note-{i:02d}/SKILL.md"
            else:
                part += 1
                dst = f"skills/note-{i:02d}/part-{part:02d}.md"
            rows.append((src, dst, p.stat().st_size))
    other = sorted(p for p in memory.rglob("*") if p.is_file() and p.relative_to(memory).as_posix() not in owned | {"MEMORY.md"})
    rows += [(p.relative_to(memory).as_posix(), f"notes/part-{j:02d}.md", p.stat().st_size) for j, p in enumerate(other, 1)]
    return rows


def build(memory: Path, out: Path, source: Path = SOURCE) -> dict:
    if out.exists():
        raise ValueError(f"{out} already exists")
    rows = plan(memory)
    filler = Filler(source.read_text(encoding="ascii"))
    notes = sorted({dst.split("/")[1] for _, dst, _ in rows if dst.startswith("skills/")})
    index = INDEX_HEAD + "".join(f"- [{n}](skills/{n}/SKILL.md)\n" for n in notes)
    overrun = 0
    for src, dst, size in rows:
        if dst == "MEMORY.md":
            head = index
        elif dst.endswith("/SKILL.md"):
            n = dst.split("/")[1]
            head = f"---\nname: {n}\ndescription: Reading notes, part {int(n[5:])}.\n---\n\n"
        else:
            head = ""
        overrun += max(0, len(head) - size)
        body = head + filler.take(max(0, size - len(head)))
        (out / dst).parent.mkdir(parents=True, exist_ok=True)
        (out / dst).write_text(body, encoding="ascii")
    real = [len((out / d).read_bytes()) for _, d, _ in rows]
    report = {"files": len(rows), "skills": len(notes), "bytes_source": sum(s for *_, s in rows), "bytes_placebo": sum(real),
              "files_exact_size": sum(r == s for r, (*_, s) in zip(real, rows)), "header_overrun_bytes": overrun,
              "source_wraps": filler.wraps, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
    report["ok"] = report["files_exact_size"] == len(rows) and report["skills"] == len(arm_logic.skills(memory))
    return report


def main(argv: list[str]) -> int:
    memory, out = resolve(Path(argv[1])), Path(argv[2])
    report = build(memory, out, Path(argv[3]) if len(argv) > 3 else SOURCE)
    out.with_name(out.name + ".placebo-report.json").write_text(json.dumps(report, indent=1) + "\n")
    print("PLACEBO", json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
