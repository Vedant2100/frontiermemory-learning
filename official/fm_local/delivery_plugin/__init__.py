"""Trial-local delivery variants. Never log skill names, terms, prompts, or skill text."""
from __future__ import annotations

import atexit
import hashlib
import json
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except Exception:  # Hermes ships PyYAML; fail closed if its plugin environment does not.
    yaml = None

HOME = Path(os.environ.get("HERMES_HOME", "/tmp/hermes"))
MEMORY = HOME / "memories"
ARM = os.environ.get("FM_DELIVERY_MODE", "")
MEMORY_SHA256 = os.environ.get("FM_DELIVERY_MEMORY_SHA256", "")
MEMORY_ENABLED = os.environ.get("FM_DELIVERY_MEMORY_ENABLED") == "1"
STOP = {"about", "after", "also", "and", "are", "for", "from", "into", "that", "the", "this", "with", "your"}
BEGIN = "<fm-memory-skill:"
END = "</fm-memory-skill>"
METRICS = {
    "delivery": ARM,
    "memory_sha256": MEMORY_SHA256,
    "skill_count": 0,
    "initial_memory_bytes": (MEMORY / "MEMORY.md").stat().st_size if MEMORY_ENABLED and (MEMORY / "MEMORY.md").is_file() else 0,
    "skills_index_bytes_observed": 0,
    "memory_skills_index_file_count": 0,
    "all_skills_index_file_count": 0,
    "memory_index_entries_observed": 0,
    "memory_index_entry_bytes_observed": 0,
    "memory_index_source_header_bytes_observed": 0,
    "memory_index_category_header_bytes_observed": 0,
    "first_request_seen": False,
    "cue_activations": 0,
    "tool_result_insertions": 0,
    "confirmed_next_request_exposures": 0,
    "inserted_bytes": 0,
    "categorized_index_rewrites": 0,
    "categorized_index_integrity_checks": 0,
    "categorized_memory_entries_before": 0,
    "categorized_memory_entries_after": 0,
    "categorized_bundled_entries_before": 0,
    "categorized_bundled_entries_after": 0,
    "categorized_index_memory_entries_observed": 0,
    "categorized_index_memory_entry_bytes_observed": 0,
    "categorized_index_original_memory_source_header_bytes_observed": 0,
    "categorized_index_category_header_bytes_observed": 0,
    "categorized_nonmemory_inventory_sha256_before": None,
    "categorized_nonmemory_inventory_sha256_after": None,
    "categorized_index_integrity_ok": True,
}


def _tokens(value: str) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", value.casefold()) if len(x) >= 4 and x not in STOP}


def _frontmatter(path: Path) -> dict:
    if yaml is None:
        return {}
    try:
        raw = path.read_bytes()[: 64 * 1024].decode("utf-8")
        if not raw.startswith("---\n"):
            return {}
        end = raw.find("\n---", 4)
        if end < 0:
            return {}
        value = yaml.safe_load(raw[4:end])
        return value if isinstance(value, dict) else {}
    except (OSError, UnicodeError, Exception):
        return {}


def _skills() -> list[dict]:
    out = []
    for path in sorted(MEMORY.glob("skills/**/SKILL.md"), key=lambda p: p.relative_to(MEMORY).as_posix()):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        meta = _frontmatter(path)
        name = str(meta.get("name") or path.parent.name)
        description = str(meta.get("description") or "")
        raw_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        out.append({"path": path, "text": text, "name": name, "description": description, "sha256": raw_digest})
    METRICS["skill_count"] = len(out)
    return out


SKILLS = _skills()
INDEX_FILES = sorted((p for p in (HOME / "skills").glob("**/SKILL.md") if p.is_file()),
                     key=lambda p: p.relative_to(HOME / "skills").as_posix())
MEMORY_SKILL_DIGESTS = {
    skill["path"].relative_to(MEMORY / "skills").as_posix(): skill["sha256"]
    for skill in SKILLS
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


MEMORY_INDEX_FILES = [
    path for path in INDEX_FILES
    if path.relative_to(HOME / "skills").as_posix() in MEMORY_SKILL_DIGESTS
    and _sha256(path) == MEMORY_SKILL_DIGESTS[path.relative_to(HOME / "skills").as_posix()]
]
MEMORY_INDEX_RELATIVE = {path.relative_to(HOME / "skills").as_posix() for path in MEMORY_INDEX_FILES}
METRICS["memory_skills_index_file_count"] = len(MEMORY_INDEX_FILES)
METRICS["all_skills_index_file_count"] = len(INDEX_FILES)
METRICS["memory_skills_index_file_bytes"] = sum(p.stat().st_size for p in MEMORY_INDEX_FILES)
METRICS["all_skills_index_file_bytes"] = sum(p.stat().st_size for p in INDEX_FILES)
PENDING: list[dict] = []
TRIGGERED: set[str] = set()
INSERTED: dict[str, str] = {}
CONFIRMED: set[str] = set()


def _get(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _all_text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_all_text(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(_all_text(v) for v in value)
    if hasattr(value, "model_dump"):
        try:
            return _all_text(value.model_dump())
        except Exception:
            return ""
    if hasattr(value, "__dict__"):
        return _all_text(vars(value))
    return ""


def _is_incomplete(event: dict) -> bool:
    if event.get("is_complete") is False or event.get("complete") is False:
        return True
    reason = str(event.get("finish_reason") or event.get("stop_reason") or "").casefold()
    if reason in {"length", "max_tokens", "incomplete", "cancelled", "canceled", "error", "failed"}:
        return True
    response = event.get("response")
    return str(_get(response, "status", "")).casefold() == "incomplete"


def _post_api_request(**event):
    if ARM != "cue" or _is_incomplete(event):
        return
    assistant = event.get("assistant_message") or event.get("message") or event.get("response")
    content = _all_text(assistant if isinstance(assistant, str) else _get(assistant, "content", ""))
    calls = _get(assistant, "tool_calls", None) or event.get("tool_calls") or []
    observed_tokens = _tokens(content + " " + _all_text(calls))
    call_matches = []
    if isinstance(calls, (list, tuple)):
        for call in calls:
            call_id = _get(call, "id") or _get(call, "tool_call_id")
            call_matches.append((str(call_id) if call_id else None, _tokens(_all_text(call))))
    activated = []
    for skill in SKILLS:
        key = skill["sha256"]
        if key in TRIGGERED:
            continue
        terms = _tokens(skill["name"] + " " + skill["description"])
        if terms & observed_tokens:
            matching_ids = [call_id for call_id, tokens in call_matches if call_id and terms & tokens]
            fallback_id = next((call_id for call_id, _ in call_matches if call_id), None)
            activated.append((skill["path"].relative_to(MEMORY).as_posix(), skill,
                              matching_ids[0] if matching_ids else fallback_id))
    for _, skill, call_id in sorted(activated, key=lambda item: item[0]):
        TRIGGERED.add(skill["sha256"])
        METRICS["cue_activations"] += 1
        PENDING.append({"skill": skill, "tool_call_id": call_id})


def _transform_tool_result(**event):
    if ARM != "cue" or not PENDING:
        return None
    call_id = event.get("tool_call_id") or event.get("call_id")
    matched = [item for item in PENDING
               if item["tool_call_id"] is None or (call_id is not None and item["tool_call_id"] == str(call_id))]
    if not matched:
        return None
    original = event.get("result", "")
    base = original if isinstance(original, str) else str(original)
    blocks = []
    matched_digests = set()
    for item in matched:
        skill = item["skill"]
        digest = skill["sha256"]
        block = f"{BEGIN}{digest}>\n{skill['text']}\n{END}"
        INSERTED[digest] = block
        blocks.append(block)
        matched_digests.add(digest)
        METRICS["inserted_bytes"] += len(skill["text"].encode("utf-8"))
    PENDING[:] = [item for item in PENDING if item not in matched]
    METRICS["tool_result_insertions"] += len(matched_digests)
    return base + "\n\n" + "\n\n".join(blocks)


def _memory_index_aliases() -> dict[str, set[str]]:
    aliases: dict[str, set[str]] = {}
    selected = {p.relative_to(HOME / "skills").as_posix() for p in MEMORY_INDEX_FILES}
    for skill in SKILLS:
        rel = skill["path"].relative_to(MEMORY / "skills").as_posix()
        if rel not in selected:
            continue
        aliases.setdefault(skill["name"], set()).add(rel)
        aliases.setdefault(Path(rel).parent.as_posix(), set()).add(rel)
        aliases.setdefault(Path(rel).parent.name, set()).add(rel)
    return aliases


MEMORY_INDEX_ALIASES = _memory_index_aliases()


def _memory_index_observed(body: str) -> tuple[int, int, int, int]:
    """Count memory skill entries, source headings, and fixed category headings."""
    visible = set()
    visible_bytes = 0
    source_headers: dict[str, str] = {}
    visible_sources = set()
    current_source = ""
    category_header_bytes = 0
    aliases = sorted(MEMORY_INDEX_ALIASES, key=len, reverse=True)

    def match_name(value: str) -> set[str]:
        for alias in aliases:
            if value == alias or value.startswith(alias + ": "):
                matches = MEMORY_INDEX_ALIASES[alias]
                return matches if len(matches) == 1 else set()
        return set()

    for line in body.splitlines():
        stripped = line.strip()
        names = re.match(r"^\s{2,}([^\n]+) \[names only\]:\s*(.*)$", line)
        if names:
            current_source = names.group(1).strip()
            found = set()
            for name in names.group(2).split(","):
                found.update(match_name(name.strip()))
            if found:
                visible.update(found)
                visible_bytes += len(line.encode("utf-8"))
                visible_sources.add(current_source)
            continue
        if stripped in {"Procedural skills:", "Environment facts:", "User preferences:"}:
            current_source = stripped[:-1]
            category_header_bytes += len(line.encode("utf-8"))
            continue
        heading = re.match(r"^\s{2,}([^:]+):\s*.*$", line)
        if heading:
            current_source = heading.group(1).strip()
            source_headers[current_source] = line
        if stripped.startswith("- "):
            entry = stripped[2:]
            found = match_name(entry)
            visible.update(found)
            if found:
                visible_bytes += len(line.encode("utf-8"))
                visible_sources.add(current_source)
    header_bytes = sum(len(source_headers[source].encode("utf-8")) for source in visible_sources
                       if source in source_headers)
    return len(visible), visible_bytes, header_bytes, category_header_bytes


def _pre_api_request(**event):
    payload = event.get("request") or event.get("messages") or event
    text = _all_text(payload)
    if not METRICS["first_request_seen"]:
        m = re.search(r"<available_skills>(.*?)</available_skills>", text, flags=re.DOTALL)
        if m:
            body = m.group(1)
            METRICS["skills_index_bytes_observed"] = len(body.encode("utf-8"))
            count, nbytes, header_bytes, category_header_bytes = _memory_index_observed(body)
            METRICS["memory_index_entries_observed"] = count
            METRICS["memory_index_entry_bytes_observed"] = nbytes
            METRICS["memory_index_source_header_bytes_observed"] = header_bytes
            METRICS["memory_index_category_header_bytes_observed"] = category_header_bytes
        METRICS["first_request_seen"] = True
    if ARM != "cue" or not INSERTED:
        return
    for digest, block in INSERTED.items():
        if digest not in CONFIRMED and block in text:
            CONFIRMED.add(digest)
            METRICS["confirmed_next_request_exposures"] += 1
            METRICS["confirmed_exposed_bytes"] = METRICS.get("confirmed_exposed_bytes", 0) + len(block.encode("utf-8"))


def _category(meta: dict) -> str:
    text = " ".join(str(meta.get(k, "")) for k in ("name", "description", "scope", "domain", "task_family")).casefold()
    if any(x in text for x in ("preference", "prefer", "writing style", "tone", "format preference")):
        return "User preferences"
    if any(x in text for x in ("environment", "version", "dependency", "repository", "toolchain", "configuration")):
        return "Environment facts"
    return "Procedural skills"


def _index_aliases() -> tuple[dict[str, set[str]], dict[str, dict]]:
    aliases: dict[str, set[str]] = {}
    metadata: dict[str, dict] = {}
    for path in INDEX_FILES:
        rel = path.relative_to(HOME / "skills").as_posix()
        meta = _frontmatter(path)
        metadata[rel] = meta
        for name in (str(meta.get("name") or ""), Path(rel).parent.as_posix(), Path(rel).parent.name):
            if name:
                aliases.setdefault(name, set()).add(rel)
    return aliases, metadata


INDEX_ALIAS_PATHS, INDEX_METADATA_BY_PATH = _index_aliases()


def _memory_entry(content: str) -> tuple[str, dict] | None:
    """Return an unambiguous HM memory-skill entry; bundled and ambiguous names stay untouched."""
    for alias in sorted(INDEX_ALIAS_PATHS, key=len, reverse=True):
        if content == alias or content.startswith(alias + ": "):
            paths = INDEX_ALIAS_PATHS[alias]
            if len(paths) != 1:
                return None
            rel = next(iter(paths))
            if rel not in MEMORY_INDEX_RELATIVE:
                return None
            return rel, INDEX_METADATA_BY_PATH.get(rel, {})
    return None


def _parse_index_entries(body: str) -> list[str] | None:
    """Extract visible skill entry payloads without headings or indentation."""
    entries = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        names_only = re.match(r"^\s{2,}[^\n]+\[names only\]:\s*(.*)$", line)
        if names_only:
            entries.extend(name.strip() for name in names_only.group(1).split(",") if name.strip())
        elif re.match(r"^\s*- ", line):
            entries.append(re.sub(r"^\s*- ", "", line, count=1))
        elif stripped in {"Procedural skills:", "Environment facts:", "User preferences:"}:
            continue
        elif re.match(r"^\s{2,}[^\n]+:\s*.*$", line):
            continue
        else:
            return None
    return entries


def _inventory_digest(entries: list[str]) -> str:
    return hashlib.sha256(json.dumps(sorted(entries), ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _categorized_index(body: str) -> str:
    """Categorize only HM skills, preserving bundled entries and all entry payloads exactly once."""
    groups = {name: [] for name in ("Procedural skills", "Environment facts", "User preferences")}
    _, _, original_memory_source_header_bytes, _ = _memory_index_observed(body)
    kept_lines = []
    memory_entries = []
    bundled_entries = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            kept_lines.append(line)
            continue
        names_only = re.match(r"^\s{2,}[^\n]+\[names only\]:\s*(.*)$", line)
        if names_only:
            names = [name.strip() for name in names_only.group(1).split(",") if name.strip()]
            retained = []
            for name in names:
                matched = _memory_entry(name)
                if matched:
                    _, meta = matched
                    groups[_category(meta)].append("- " + name)
                    memory_entries.append(name)
                else:
                    retained.append(name)
                    bundled_entries.append(name)
            if len(retained) == len(names):
                kept_lines.append(line)
            elif retained:
                kept_lines.append(line[:names_only.start(1)] + ", ".join(retained))
        elif re.match(r"^\s*- ", line):
            entry = re.sub(r"^\s*- ", "", line, count=1)
            matched = _memory_entry(entry.strip())
            if matched:
                _, meta = matched
                groups[_category(meta)].append("- " + entry)
                memory_entries.append(entry)
            else:
                kept_lines.append(line)
                bundled_entries.append(entry)
        elif re.match(r"^\s{2,}[^\n]+:\s*.*$", line):
            kept_lines.append(line)
        else:
            raise ValueError("unknown pinned Hermes skill-index format; refusing categorized rewrite")
    if not memory_entries:
        raise ValueError("categorized arm found no unambiguous HM memory-skill entries")

    updated = "\n".join(kept_lines)
    if body.endswith("\n"):
        updated += "\n"
    category_text = "\n\n".join(f"{heading}:\n" + "\n".join(f"  {entry}" for entry in groups[heading])
                                   for heading in groups if groups[heading])
    updated += ("" if not updated else ("" if updated.endswith("\n\n") else "\n" if updated.endswith("\n") else "\n\n"))
    updated += category_text

    original_inventory = _parse_index_entries(body)
    updated_inventory = _parse_index_entries(updated)
    if original_inventory is None or updated_inventory is None:
        raise ValueError("categorized index inventory could not be parsed")
    from collections import Counter
    if Counter(original_inventory) != Counter(updated_inventory):
        raise ValueError("categorized rewrite changed or duplicated a skill entry")
    output_memory = [entry for entry in updated_inventory if _memory_entry(entry.strip())]
    output_bundled = [entry for entry in updated_inventory if not _memory_entry(entry.strip())]
    if Counter(memory_entries) != Counter(output_memory) or Counter(bundled_entries) != Counter(output_bundled):
        raise ValueError("categorized rewrite did not preserve memory and bundled entry inventories")

    categorized_count, categorized_entry_bytes, _, categorized_header_bytes = _memory_index_observed(updated)
    if categorized_count != len({matched[0] for entry in output_memory if (matched := _memory_entry(entry.strip()))}):
        raise ValueError("categorized request-visible memory skill count differs from its inventory")

    METRICS["categorized_index_integrity_checks"] += 1
    METRICS["categorized_memory_entries_before"] = len(memory_entries)
    METRICS["categorized_memory_entries_after"] = len(output_memory)
    METRICS["categorized_bundled_entries_before"] = len(bundled_entries)
    METRICS["categorized_bundled_entries_after"] = len(output_bundled)
    METRICS["categorized_nonmemory_inventory_sha256_before"] = _inventory_digest(bundled_entries)
    METRICS["categorized_nonmemory_inventory_sha256_after"] = _inventory_digest(output_bundled)
    METRICS["categorized_index_memory_entries_observed"] = categorized_count
    METRICS["categorized_index_memory_entry_bytes_observed"] = categorized_entry_bytes
    METRICS["categorized_index_original_memory_source_header_bytes_observed"] = original_memory_source_header_bytes
    METRICS["categorized_index_category_header_bytes_observed"] = categorized_header_bytes
    return updated


def _rewrite(value):
    if isinstance(value, str):
        pattern = re.compile(r"<available_skills>(.*?)</available_skills>", flags=re.DOTALL)
        def replace(match):
            updated = _categorized_index(match.group(1))
            if updated != match.group(1):
                METRICS["categorized_index_rewrites"] += 1
            return "<available_skills>" + updated + "</available_skills>"
        return pattern.sub(replace, value)
    if isinstance(value, list):
        return [_rewrite(item) for item in value]
    if isinstance(value, dict):
        return {key: _rewrite(item) for key, item in value.items()}
    return value


def _categorized_request(**event):
    request = event.get("request")
    if ARM != "categorized" or not isinstance(request, dict):
        return None
    rewritten = _rewrite(request)
    return {"request": rewritten, "source": "fm-delivery-c2", "reason": "fixed categorized skill index"}


def _emit_metrics():
    print("FM_DELIVERY_METRICS=" + json.dumps(METRICS, sort_keys=True, separators=(",", ":")), file=sys.stderr, flush=True)


def register(ctx):
    if ARM not in {"cue", "scoped", "categorized", "observe"} or not re.fullmatch(r"[0-9a-f]{64}", MEMORY_SHA256):
        raise RuntimeError("delivery plugin environment is incomplete")
    ctx.register_hook("pre_api_request", _pre_api_request)
    if ARM == "cue":
        ctx.register_hook("post_api_request", _post_api_request)
        ctx.register_hook("transform_tool_result", _transform_tool_result)
    if ARM == "categorized":
        ctx.register_middleware("llm_request", _categorized_request)
    atexit.register(_emit_metrics)
