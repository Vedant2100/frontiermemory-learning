"""Shown vs opened: for each trial of a Harbor job run with the Hermes task agent, did the agent open memory, and when?

Reads each trial's result.json (memory digest, memory file list, exposure arm) and its Hermes tool calls, from
agent/hermes-session.jsonl (`hermes sessions export`, as MemoryHermes saves it) or, failing that, agent/trajectory.json (ATIF).
Writes one JSON line per trial and a per-arm summary. Counts, kinds and paths relative to the memory root only, never contents.

MemoryHermes puts the memory folder at $HERMES_HOME/memories and its skills at $HERMES_HOME/skills, with HERMES_HOME=/tmp/hermes.
An "open" is any of:
  skill_view of a memory skill (by name)                       -> SKILL.md, or the linked file's kind if file_path is given
  read_file of a memory path                                   -> kind of that file
  search_files with a memory path                              -> "search"
  terminal / execute_code naming a memory path with a read verb (cat, head, grep, sed, python open, ...) -> kind of the file named,
                                                                  "search" for grep/rg/find over a directory
Naming a memory path without a read verb (ls) counts as "listed", not opened. A terminal command is only seen when it names
.../memories or .../skills; one over all of /tmp/hermes is missed (read_file and search_files on /tmp/hermes are caught). Viewing one of Hermes's bundled skills is counted
separately and isn't a memory open.
Usage: python3 -I scripts/memory_access.py JOB_DIR [JOB_DIR ...] [--arm NAME] [--out results/official/memory-access.jsonl]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

HOME = "/tmp/hermes"
ROOTS = (f"{HOME}/memories/", f"{HOME}/skills/", "$HERMES_HOME/memories/", "$HERMES_HOME/skills/", "${HERMES_HOME}/memories/",
         "${HERMES_HOME}/skills/")  # not ~/: the container's HOME isn't HERMES_HOME
READ_VERB = re.compile(r"\b(cat|head|tail|less|more|bat|nl|sed|awk|grep|egrep|rg|jq|wc|strings|xxd|od|python3?|open|read_text|readlines?)\b")
SEARCH_VERB = re.compile(r"\b(grep|egrep|rg|find|ack|ag)\b")
PATH_CHARS = r"[^\s'\"`;|&<>()]*"


def kind_of(rel: str) -> str:
    name = PurePosixPath(rel).name
    return name if name in ("MEMORY.md", "SKILL.md", "USER.md") else "other"


class Memory:
    """The trial's memory, from the file list MemoryHermes records in result.json."""

    def __init__(self, files: list[str]):
        self.files = set(files)
        self.skills = {PurePosixPath(f).parent.name: PurePosixPath(f).parent.as_posix() for f in files if PurePosixPath(f).name == "SKILL.md"}

    def rel(self, path: str) -> str | None:
        """Memory-root-relative path of a container path, or None if it isn't memory."""
        path = path.rstrip("/") + "/"  # so a bare /tmp/hermes/memories matches too
        if path.endswith((f"{HOME}/", "$HERMES_HOME/", "${HERMES_HOME}/")):  # e.g. search_files over all of HERMES_HOME
            return "."
        for root in ROOTS:
            if root in path:
                tail = path.split(root, 1)[1].strip("/")
                rel = tail if "memories/" in root else f"skills/{tail}" if tail else "skills"
                if rel.startswith("skills/"):  # $HERMES_HOME/skills also holds Hermes's bundled skills
                    first = tail.split("/", 1)[0] if tail else ""
                    if first and not any(s == rel or s.startswith(f"skills/{first}") or rel.startswith(s) for s in self.skills.values()):
                        return None
                return rel or "."
        return None


def tool_calls(trial: Path) -> list[tuple[int, str, dict]]:
    """(assistant turn index, tool name, arguments) in order."""
    out = []
    session = trial / "agent" / "hermes-session.jsonl"
    if session.exists() and session.read_text(errors="ignore").strip():
        turn = -1
        for line in session.read_text(errors="ignore").splitlines():
            if not line.strip():
                continue
            for msg in json.loads(line).get("messages") or []:
                if msg.get("role") != "assistant":
                    continue
                turn += 1
                for call in msg.get("tool_calls") or []:
                    fn = call.get("function") or {}
                    out.append((turn, fn.get("name") or call.get("name") or "", _args(fn.get("arguments", call.get("arguments")))))
        return out
    traj = trial / "agent" / "trajectory.json"
    if traj.exists():
        data = json.loads(traj.read_text(errors="ignore"))
        steps = data.get("steps", data if isinstance(data, list) else [])
        for turn, step in enumerate(s for s in steps if s.get("source", "agent") == "agent"):
            for call in step.get("tool_calls") or []:
                out.append((turn, call.get("function_name") or call.get("name") or "", _args(call.get("arguments"))))
    return out


def _args(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {"_": str(value)}
    except (TypeError, ValueError):
        return {"_": str(raw)}


def classify(name: str, args: dict, memory: Memory) -> tuple[str, list[tuple[str, str]]]:
    """('open'|'listed'|'bundled_skill'|'none', [(kind, rel path)])."""
    if name == "skill_view":
        skill = str(args.get("name", "")).rsplit("/", 1)[-1].rsplit(":", 1)[-1]
        if skill not in memory.skills:
            return "bundled_skill", []
        linked = str(args.get("file_path") or "")
        rel = f"{memory.skills[skill]}/{linked}".rstrip("/") if linked else f"{memory.skills[skill]}/SKILL.md"
        return "open", [(kind_of(rel), rel)]
    if name == "read_file":
        rel = memory.rel(str(args.get("path", "")))
        return ("open", [(kind_of(rel), rel)]) if rel else ("none", [])
    if name == "search_files":
        rel = memory.rel(str(args.get("path", "")))
        return ("open", [("search", rel)]) if rel else ("none", [])
    if name in ("terminal", "execute_code"):
        text = str(args.get("command") or args.get("code") or args.get("_") or "")
        rels = sorted({r for m in re.finditer(PATH_CHARS + r"(?:memories|skills)/?" + PATH_CHARS, text) if (r := memory.rel(m.group(0)))})
        if not rels:
            return "none", []
        if not READ_VERB.search(text):
            return "listed", [("listed", r) for r in rels]
        hits = [(kind_of(r), r) for r in rels if PurePosixPath(r).suffix or r in memory.files]
        if not hits or SEARCH_VERB.search(text):
            hits += [("search", r) for r in rels if not (PurePosixPath(r).suffix or r in memory.files)]
        return "open", hits or [("search", rels[0])]
    return "none", []


def measure(trial: Path, arm: str | None) -> dict:
    result = json.loads((trial / "result.json").read_text())
    meta = (result.get("agent_result") or {}).get("metadata") or {}
    fm = meta.get("frontier_memory") or {}
    exposure = (meta.get("fm_exposure") or {}).get("exposure") or arm
    memory = Memory(fm.get("files") or [])
    calls = tool_calls(trial)
    opens, kinds, paths, listed, bundled = [], Counter(), set(), 0, 0
    for i, (turn, name, args) in enumerate(calls):
        what, hits = classify(name, args, memory)
        if what == "open":
            opens.append((i, turn))
            for kind, rel in hits:
                kinds[kind] += 1
                paths.add(rel)
        listed += what == "listed"
        bundled += what == "bundled_skill"
    reward = ((result.get("verifier_result") or {}).get("rewards") or {}).get("reward")
    return {"trial": trial.name, "task": result.get("task_name"), "reward": reward, "memory_sha256": fm.get("sha256"),
            "exposure": exposure, "has_memory": bool(fm), "tool_calls": len(calls), "opened": bool(opens),
            "opens": len(opens), "open_kinds": dict(kinds), "first_open_turn": opens[0][1] if opens else None,
            "tool_calls_before_first_open": opens[0][0] if opens else None, "listed_only_calls": listed,
            "bundled_skill_views": bundled, "opened_paths": sorted(paths)}


def summarise(rows: list[dict]) -> dict:
    by = defaultdict(list)
    for r in rows:
        by[r["exposure"] or ("hm" if r["has_memory"] else "no-memory")].append(r)
    out = {}
    for arm, rs in sorted(by.items()):
        opened = [r for r in rs if r["opened"]]
        kinds = Counter()
        for r in rs:
            kinds.update(r["open_kinds"])
        before = sorted(r["tool_calls_before_first_open"] for r in opened)
        out[arm] = {"trials": len(rs), "opened": len(opened), "share_opened": round(len(opened) / len(rs), 3) if rs else None,
                    "open_kinds": dict(kinds), "median_tool_calls_before_first_open": before[len(before) // 2] if before else None,
                    "median_tool_calls": sorted(r["tool_calls"] for r in rs)[len(rs) // 2] if rs else None,
                    "memory_digests": sorted({r["memory_sha256"] for r in rs if r["memory_sha256"]})}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("jobs", nargs="+", type=Path)
    ap.add_argument("--arm", help="arm label for trials whose metadata names none")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    rows = [measure(t, args.arm) for job in args.jobs for t in sorted(job.iterdir()) if (t / "result.json").exists()]
    text = "".join(json.dumps(r) + "\n" for r in rows)
    if args.out:
        args.out.write_text(text)
        args.out.with_suffix(".summary.json").write_text(json.dumps(summarise(rows), indent=1) + "\n")
    else:
        sys.stdout.write(text)
    print(json.dumps(summarise(rows), indent=1), file=sys.stderr)


if __name__ == "__main__":
    main()
