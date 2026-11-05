"""Shown vs opened: for each Harbor trial, estimate start-of-context memory and count later memory opens.

Reads each trial's result.json (memory digest, memory file list, exposure arm) and its agent tool calls, from
agent/hermes-session.jsonl (`hermes sessions export`, as MemoryHermes saves it) or, failing that, agent/trajectory.json (ATIF).
Supports Hermes, Codex and Claude Code file/tool paths. Writes one JSON line per trial and a per-arm summary.
Counts, kinds and paths relative to the memory root only, never contents.

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
Shown-byte estimates use the pinned harness rules and the validated generation folder; they are not request-body captures.
Codex uses its 2,500-token summary window (10,000-byte head/tail estimate), Claude Code its first 200 lines or 25 KB,
and Hermes its complete MEMORY.md. E-all adds its full-file injection and counts observed memory-skill index entries.
`--harness exposure-none|exposure-all` uses the adapter's counts.

Usage: python3 -I scripts/memory_access.py JOB_DIR [JOB_DIR ...] [--arm NAME] [--harness H] [--memory-dir DIR] [--out PATH]
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
         "${HERMES_HOME}/skills/", "$CODEX_HOME/memories/", "${CODEX_HOME}/memories/", "/root/.codex/memories/",
         "/home/oai/.codex/memories/", "/root/.claude/memory/", "/home/oai/.claude/memory/")
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
        self.skills: dict[str, set[str]] = defaultdict(set)
        for file in files:
            p = PurePosixPath(file)
            if p.name == "SKILL.md":
                self.skills[p.parent.name].add(p.parent.as_posix())
        self.skill_paths = {path for paths in self.skills.values() for path in paths}

    def rel(self, path: str) -> str | None:
        """Memory-root-relative path of a container path, or None if it isn't memory."""
        path = path.replace("\\", "/")
        path = path.rstrip("/") + "/"  # so a bare /tmp/hermes/memories matches too
        if path.endswith((f"{HOME}/", "$HERMES_HOME/", "${HERMES_HOME}/")):  # e.g. search_files over all of HERMES_HOME
            return "."
        for root in ROOTS:
            if root in path:
                tail = path.split(root, 1)[1].strip("/")
                if root.rstrip("/").endswith("/skills"):
                    rel = f"skills/{tail}" if tail else "skills"
                    first = tail.split("/", 1)[0] if tail else ""
                    if first:
                        skill_root = f"skills/{first}"
                        if not any(
                            s == skill_root or s.startswith(skill_root + "/")
                            or skill_root.startswith(s + "/") or rel == s or rel.startswith(s + "/")
                            for s in self.skill_paths
                        ):
                            return None  # exclude Hermes's bundled skills
                else:
                    rel = tail or "."
                return rel or "."
        # Claude Code project memory lives under ~/.claude/projects/<project>/memory/.
        if "/.claude/projects/" in path:
            tail = path.split("/.claude/projects/", 1)[1]
            if "/memory/" in tail:
                return tail.split("/memory/", 1)[1].strip("/") or "."
        # Absolute or relative paths supplied directly by Read/Grep can omit the home prefix.
        for marker in ("/memories/", "/memory/"):
            if marker in path:
                tail = path.rsplit(marker, 1)[1].strip("/")
                if tail in self.files or any(f.startswith(tail + "/") for f in self.files):
                    return tail or "."
        stripped = path.strip("/")
        if stripped in self.files:
            return stripped
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
    if name in ("skill_view", "Skill"):
        raw_skill = str(args.get("name", "")).rsplit(":", 1)[-1]
        skill = raw_skill.rsplit("/", 1)[-1]
        candidates = memory.skills.get(skill, set())
        if not candidates:
            return "bundled_skill", []
        if len(candidates) > 1:
            exact = {c for c in candidates if raw_skill == c or raw_skill.endswith("/" + c)}
            if len(exact) == 1:
                candidates = exact
            else:
                # Count the view without choosing one of two same-named skills incorrectly.
                return "open", [("SKILL.md", f"skills/{skill}/SKILL.md")]
        root = next(iter(candidates))
        linked = str(args.get("file_path") or "")
        rel = f"{root}/{linked}".rstrip("/") if linked else f"{root}/SKILL.md"
        return "open", [(kind_of(rel), rel)]
    if name in ("read_file", "Read", "read"):
        rel = memory.rel(str(args.get("path") or args.get("file_path") or args.get("file", "")))
        return ("open", [(kind_of(rel), rel)]) if rel else ("none", [])
    if name in ("search_files", "Grep", "Glob", "grep", "glob", "Search"):
        rel = memory.rel(str(args.get("path") or args.get("file_path") or args.get("pattern") or args.get("glob", "")))
        return ("open", [("search", rel)]) if rel else ("none", [])
    if name in ("terminal", "execute_code", "Bash", "bash", "shell", "shell_command", "exec_command"):
        text = str(args.get("command") or args.get("cmd") or args.get("code") or args.get("command_string") or args.get("_") or "")
        pattern = PATH_CHARS + r"(?:memories|skills)/?" + PATH_CHARS
        pattern += r"|" + PATH_CHARS + r"/\.claude/projects/" + PATH_CHARS + r"/memory/?" + PATH_CHARS
        rels = sorted({r for m in re.finditer(pattern, text) if (r := memory.rel(m.group(0)))})
        if not rels:
            return "none", []
        if not READ_VERB.search(text):
            return "listed", [("listed", r) for r in rels]
        hits = [(kind_of(r), r) for r in rels if PurePosixPath(r).suffix or r in memory.files]
        if not hits or SEARCH_VERB.search(text):
            hits += [("search", r) for r in rels if not (PurePosixPath(r).suffix or r in memory.files)]
        return "open", hits or [("search", rels[0])]
    return "none", []


def head_tail(data: bytes, limit: int) -> bytes:
    if len(data) <= limit:
        return data
    head = limit // 2
    return data[:head] + b"\n" + data[-(limit - head):]


def delivery_metrics(trial: Path) -> dict:
    marker = "FM_DELIVERY_METRICS="
    found = []
    for path in (trial / "agent").rglob("*"):
        if not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
            continue
        try:
            for line in path.read_text(errors="ignore").splitlines():
                if marker in line:
                    value = json.loads(line.split(marker, 1)[1].strip())
                    if isinstance(value, dict):
                        found.append(value)
        except (OSError, json.JSONDecodeError):
            continue
    return found[0] if len(found) == 1 else {}


def shown_metrics(memory_root: Path | None, harness: str, exposure: dict, delivery: dict,
                  plugin_metrics: dict) -> dict:
    """Count the startup memory specified by the harness without exposing its text."""
    empty = {"memory_bytes": None, "memory_index_bytes": None, "shown_bytes_estimate": None,
             "shown_tokens_estimate": None, "shown_share_of_index": None, "shown_rule": None}
    if memory_root is None:
        return empty
    files = [p for p in memory_root.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    index = memory_root / "MEMORY.md"
    if not index.is_file():
        return {**empty, "memory_bytes": total}
    body = index.read_bytes()
    if harness == "codex":
        summary = memory_root / "memory_summary.md"
        src = summary.read_bytes() if summary.is_file() else body
        shown = head_tail(src, 2500 * 4)
        rule = "codex_2500_token_head_tail_4_bytes_per_token"
    elif harness == "claude-code":
        shown = b"\n".join(body.split(b"\n")[:200])[:25 * 1024]
        rule = "claude_first_200_lines_or_25_kib"
    elif harness == "exposure-none":
        shown = b""
        rule = "exposure_none"
    elif harness == "exposure-all":
        rule = "exposure_all_full_files"
    elif harness.startswith("delivery-"):
        mode = delivery.get("delivery")
        if mode == "cue":
            shown_bytes = plugin_metrics.get("confirmed_exposed_bytes", 0)
            rule = "cue_confirmed_skill_text_present_in_next_request"
            entry_bytes = category_header_bytes = source_header_bytes = None
        else:
            initial = plugin_metrics.get("initial_memory_bytes")
            if mode == "categorized":
                index = plugin_metrics.get("categorized_index_memory_entry_bytes_observed")
                source_header = plugin_metrics.get("categorized_index_original_memory_source_header_bytes_observed")
                category_header = plugin_metrics.get("categorized_index_category_header_bytes_observed")
                rule = "memory_md_plus_categorized_memory_entries_and_source_and_category_headers"
            else:
                index = plugin_metrics.get("memory_index_entry_bytes_observed")
                source_header = plugin_metrics.get("memory_index_source_header_bytes_observed")
                category_header = 0
                rule = "memory_md_plus_observed_memory_skill_entries_and_source_headers"
            entry_bytes, source_header_bytes, category_header_bytes = index, source_header, category_header
            shown_bytes = (initial + index + source_header + category_header
                           if all(isinstance(value, int) and not isinstance(value, bool)
                                  for value in (initial, index, source_header, category_header)) else None)
        return {"memory_bytes": total, "memory_index_bytes": len(body),
                "shown_bytes_estimate": shown_bytes,
                "shown_tokens_estimate": round(shown_bytes / 4) if isinstance(shown_bytes, int) else None,
                "shown_share_of_index": None,
                "shown_rule": rule,
                "exposure_injected_bytes": None,
                "hm_startup_memory_md_bytes": plugin_metrics.get("initial_memory_bytes"),
                "hm_startup_memory_skill_entries_bytes": entry_bytes,
                "hm_startup_memory_skill_source_header_bytes": source_header_bytes,
                "hm_startup_memory_skill_category_header_bytes": category_header_bytes,
                "delivery_cue_activations": plugin_metrics.get("cue_activations"),
                "delivery_tool_result_insertions": plugin_metrics.get("tool_result_insertions"),
                "delivery_confirmed_next_request_exposures": plugin_metrics.get("confirmed_next_request_exposures"),
                "delivery_confirmed_exposed_bytes": plugin_metrics.get("confirmed_exposed_bytes", 0),
                "delivery_initial_memory_bytes": plugin_metrics.get("initial_memory_bytes"),
                "delivery_skills_index_bytes_observed_total": plugin_metrics.get("skills_index_bytes_observed"),
                "delivery_memory_index_entries_observed": plugin_metrics.get("memory_index_entries_observed"),
                "delivery_memory_index_entry_bytes_observed": plugin_metrics.get("memory_index_entry_bytes_observed"),
                "delivery_memory_index_source_header_bytes_observed": plugin_metrics.get("memory_index_source_header_bytes_observed"),
                "delivery_categorized_memory_index_entry_bytes_observed": plugin_metrics.get("categorized_index_memory_entry_bytes_observed"),
                "delivery_categorized_source_header_bytes_observed": plugin_metrics.get("categorized_index_original_memory_source_header_bytes_observed"),
                "delivery_categorized_category_header_bytes_observed": plugin_metrics.get("categorized_index_category_header_bytes_observed"),
                "delivery_memory_skills_index_file_count": plugin_metrics.get("memory_skills_index_file_count"),
                "delivery_memory_skills_index_file_bytes": plugin_metrics.get("memory_skills_index_file_bytes"),
                "delivery_all_skills_index_file_count": plugin_metrics.get("all_skills_index_file_count"),
                "delivery_all_skills_index_file_bytes": plugin_metrics.get("all_skills_index_file_bytes")}
    else:
        shown = body
        rule = "hermes_full_memory_index"
    if harness == "exposure-all":
        md_bytes = exposure.get("memory_md_bytes")
        index_bytes = plugin_metrics.get("memory_index_entry_bytes_observed")
        header_bytes = plugin_metrics.get("memory_index_source_header_bytes_observed", 0)
        injected_bytes = exposure.get("injected_bytes")
        shown_bytes = (md_bytes + index_bytes + header_bytes + injected_bytes
                       if all(isinstance(value, int) and not isinstance(value, bool)
                              for value in (md_bytes, index_bytes, header_bytes, injected_bytes)) else None)
    else:
        shown_bytes = len(shown)
    return {"memory_bytes": total, "memory_index_bytes": len(body), "shown_bytes_estimate": shown_bytes,
            "shown_tokens_estimate": round(shown_bytes / 4) if isinstance(shown_bytes, int) else None,
            "shown_share_of_index": (round(shown_bytes / len(body), 4) if isinstance(shown_bytes, int) and len(body)
                                     and harness not in {"exposure-all", "exposure-none"} else None),
            "shown_rule": "hm_memory_md_plus_observed_memory_skill_index_plus_full_file_injection" if harness == "exposure-all" else rule,
            "exposure_injected_bytes": exposure.get("injected_bytes") if harness == "exposure-all" else None,
            "hm_startup_memory_md_bytes": exposure.get("memory_md_bytes") if harness == "exposure-all" else None,
            "hm_startup_memory_skill_entries_bytes": plugin_metrics.get("memory_index_entry_bytes_observed") if harness == "exposure-all" else None,
            "hm_startup_memory_skill_source_header_bytes": plugin_metrics.get("memory_index_source_header_bytes_observed") if harness == "exposure-all" else None,
            "delivery_activated_skills": delivery.get("activated_skills") if delivery else None,
            "delivery_transmitted_skills": delivery.get("transmitted_skills") if delivery else None}


def measure(trial: Path, arm: str | None, harness: str = "hermes", memory_root: Path | None = None) -> dict:
    result = json.loads((trial / "result.json").read_text())
    meta = (result.get("agent_result") or {}).get("metadata") or {}
    fm = meta.get("frontier_memory") or {}
    exposure = (meta.get("fm_exposure") or {}).get("exposure") or arm
    delivery = meta.get("fm_delivery") or {}
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
    plugin_metrics = delivery_metrics(trial) if harness.startswith(("delivery-", "exposure-")) else {}
    metrics = shown_metrics(memory_root, harness, meta.get("fm_exposure") or {}, delivery, plugin_metrics)
    return {"trial": trial.name, "task": result.get("task_name"), "reward": reward, "harness": harness,
            "memory_sha256": fm.get("sha256"),
            "delivery": delivery.get("delivery"),
            "exposure": exposure, "has_memory": bool(fm), "tool_calls": len(calls), "opened": bool(opens),
            "opens": len(opens), "open_kinds": dict(kinds), "first_open_turn": opens[0][1] if opens else None,
            "tool_calls_before_first_open": opens[0][0] if opens else None, "listed_only_calls": listed,
            **metrics,
            "bundled_skill_views": bundled, "opened_paths": sorted(paths)}


def summarise(rows: list[dict]) -> dict:
    by = defaultdict(list)
    for r in rows:
        by[r.get("delivery") or r["exposure"] or ("hm" if r["has_memory"] else "no-memory")].append(r)
    out = {}
    for arm, rs in sorted(by.items()):
        opened = [r for r in rs if r["opened"]]
        kinds = Counter()
        for r in rs:
            kinds.update(r["open_kinds"])
        before = sorted(r["tool_calls_before_first_open"] for r in opened)
        shown = sorted(r["shown_bytes_estimate"] for r in rs if isinstance(r.get("shown_bytes_estimate"), int))
        out[arm] = {"trials": len(rs), "opened": len(opened), "share_opened": round(len(opened) / len(rs), 3) if rs else None,
                    "open_kinds": dict(kinds), "median_tool_calls_before_first_open": before[len(before) // 2] if before else None,
                    "median_tool_calls": sorted(r["tool_calls"] for r in rs)[len(rs) // 2] if rs else None,
                    "shown_bytes_median": shown[len(shown) // 2] if shown else None,
                    "shown_tokens_median": round(shown[len(shown) // 2] / 4) if shown else None,
                    "delivery_cue_activations": sum(r.get("delivery_cue_activations") or 0 for r in rs),
                    "delivery_tool_result_insertions": sum(r.get("delivery_tool_result_insertions") or 0 for r in rs),
                    "delivery_confirmed_next_request_exposures": sum(r.get("delivery_confirmed_next_request_exposures") or 0 for r in rs),
                    "delivery_confirmed_exposed_bytes": sum(r.get("delivery_confirmed_exposed_bytes") or 0 for r in rs),
                    "memory_digests": sorted({r["memory_sha256"] for r in rs if r["memory_sha256"]})}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("jobs", nargs="+", type=Path)
    ap.add_argument("--arm", help="arm label for trials whose metadata names none")
    ap.add_argument("--harness", default="hermes", choices=("hermes", "codex", "claude-code", "exposure-none", "exposure-all",
                                                               "delivery-cue", "delivery-scoped", "delivery-categorized"))
    ap.add_argument("--memory-dir", type=Path, help="validated generation memory root, used for count-only shown-byte estimates")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    memory_root = args.memory_dir.resolve() if args.memory_dir else None
    rows = [measure(t, args.arm, args.harness, memory_root) for job in args.jobs for t in sorted(job.iterdir()) if (t / "result.json").exists()]
    text = "".join(json.dumps(r) + "\n" for r in rows)
    if args.out:
        args.out.write_text(text)
        args.out.with_suffix(".summary.json").write_text(json.dumps(summarise(rows), indent=1) + "\n")
    else:
        sys.stdout.write(text)
    print(json.dumps(summarise(rows), indent=1), file=sys.stderr)


if __name__ == "__main__":
    main()
