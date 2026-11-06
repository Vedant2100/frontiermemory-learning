"""Pure rules for the exploratory delivery arms (results/preregistration-arms.md). Standard library only, so the
same code runs in the guest (arm_hermes.py, cue_plugin) and in host tests. No rule reads task results.

  skills(memory_dir)            memory skills: every folder holding SKILL.md, with its frontmatter name and description
  bm25_select(instruction, ...) scoped arm: Okapi BM25 over skill bodies, query = task instruction, top K_SCOPED
  categorize(skill)             categorized arm: one of CATEGORIES by fixed keyword counts over name + description
  cue_terms / cue_match         cue arm: a skill fires when a tool call shares >= CUE_MIN_SHARED terms with its name + description
"""

from __future__ import annotations

import math
import re
import shutil
from pathlib import Path

TOKEN = re.compile(r"[a-z0-9]+")
# Generic words that would make every skill match every call. Fixed before any run.
STOP = frozenset("""
about after again also always among another because been before being below between both cannot could does doing done
down during each either every file files first from have having here into itself just know last like line lines make
many more most much must need needs never next only other over same should since some such than that their them then
there these they this those through under until upon used uses using very want were what when where which while will
with within without would your task tasks agent work true false none null json yaml path paths text value values name
names description data output input result results test tests
skill skills memory memories hermes home learned
""".split())  # last line: words of the memory's own paths (/tmp/hermes/memories/skills/<x>/SKILL.md), never a task cue

K_SCOPED = 3            # SkillsBench (arXiv 2602.12670): 2-3 focused skills beat larger bundles; fixed before any run
BM25_K1, BM25_B = 1.2, 0.75  # Robertson & Zaragoza (2009) defaults, as in Lucene
CUE_MIN_SHARED = 2      # distinct shared terms; one shared word fires on almost any call
CATEGORIES = {  # directory name -> (heading text for DESCRIPTION.md, keywords). Order breaks ties; no hit -> procedures
    "memory-user-preferences": ("Saved memory: user preferences and conventions to follow",
                                ("prefer", "preference", "preferences", "user", "users", "style", "convention",
                                 "conventions", "tone", "wording", "format", "formatting", "naming", "feedback")),
    "memory-environment-facts": ("Saved memory: facts about environments, tools, paths and versions",
                                 ("environment", "install", "installed", "version", "versions", "docker", "dependency",
                                  "dependencies", "config", "configuration", "setup", "port", "endpoint", "package",
                                  "packages", "library", "directory", "repository", "database", "schema", "api")),
    "memory-procedures": ("Saved memory: procedures and workflows that worked before", ()),
}
FALLBACK_CATEGORY = "memory-procedures"
# Fixed texts, here so the guest-side check (arm_check.py, system Python) can verify exactly what reached the model.
READ_FIRST = ("Saved memory from earlier work is available: the MEMORY.md block and the skills listed in <available_skills>. "
              "Before you start the task, check them and open any saved skill that may be relevant.")
RECORDS_TARGET = "/tmp/hermes/records"  # $HERMES_HOME/records (frontier_memory.agents.hermes.ACTOR_HOME)
POINTER = {"raw": "Records of {n} earlier agent work sessions (one JSON file each, with the outcome) are in {path}. "
                  "Search them with your tools if they could help with this task.",
           "evidence": "Records of {n} earlier agent work sessions on tasks like this one (one JSON file each, with the "
                       "outcome) are in {path}. Search them with your tools if they could help with this task."}
GENERATOR_ADDED_RULES = (  # appended to hermes_dream.LEARN_REQUEST by generator_hermes.py; sources there
    " Write each skill's description in the third person, saying both what the skill does and when to use it, with the"
    " specific task families, repositories, file types or tools it applies to."
    " Keep every distinct user preference, environment fact (paths, versions, commands, file names) and failure mode you"
    " find as its own specific item; do not merge or drop items to make the skill shorter."
    " Prefer a few focused skills over one exhaustive skill."
)
CUE_PLUGIN = "fm-cue"


def available_skills(system_prompt: str) -> str:
    """The <available_skills> block of a Hermes system prompt ("" if none)."""
    m = re.search(r"<available_skills>(.*?)</available_skills>", system_prompt or "", flags=re.DOTALL)
    return m.group(1) if m else ""


def tokens(text: str, min_len: int = 2) -> list[str]:
    return [t for t in TOKEN.findall(text.casefold()) if len(t) >= min_len]


def frontmatter(text: str) -> dict[str, str]:
    """name/description from a leading '---' block; enough for SKILL.md (flat `key: value` lines)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return out
        key, sep, value = line.partition(":")
        if sep and not line.startswith((" ", "\t")):
            out[key.strip()] = value.strip().strip("'\"")
    return {}


def skills(memory_dir: Path) -> list[dict]:
    """Memory skills in sorted path order. `rel` is the skill folder relative to memory_dir/skills."""
    root = memory_dir / "skills"
    out = []
    for f in sorted(root.rglob("SKILL.md")) if root.is_dir() else []:
        text = f.read_text(encoding="utf-8", errors="replace")
        meta = frontmatter(text)
        rel = f.parent.relative_to(root).as_posix()
        out.append({"rel": rel, "leaf": f.parent.name, "name": meta.get("name") or f.parent.name,
                    "description": meta.get("description", ""), "text": text})
    return out


def skill_files(skill_root: Path, rel: str, all_rels: list[str]) -> list[Path]:
    """Files of one skill folder, leaving out any nested skill folder (it is a skill of its own)."""
    nested = [skill_root / r for r in all_rels if r != rel and (r.startswith(rel + "/") or rel == "")]
    return sorted(p for p in (skill_root / rel).rglob("*") if p.is_file() and not any(p.is_relative_to(n) for n in nested))


def build_skills_dir(memory_dir: Path, out: Path, picks: list[tuple[str, str]], descriptions: dict[str, str]) -> None:
    """Copy each (skill rel, target rel) into out; write DESCRIPTION.md category headings. Fails on a target clash."""
    root = memory_dir / "skills"
    all_rels = [s["rel"] for s in skills(memory_dir)]
    for rel, target in picks:
        if (out / target).exists():
            raise ValueError("two memory skills map to the same indexed folder")
        for f in skill_files(root, rel, all_rels):
            dest = out / target / f.relative_to(root / rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, dest)
    for cat, text in descriptions.items():
        (out / cat).mkdir(parents=True, exist_ok=True)
        (out / cat / "DESCRIPTION.md").write_text(f"---\ndescription: {text}\n---\n", encoding="utf-8")


def bm25_scores(query: str, docs: list[str]) -> list[float]:
    q = set(tokens(query))
    toks = [tokens(d) for d in docs]
    n = len(docs)
    if not n:
        return []
    avg = sum(map(len, toks)) / n or 1.0
    df = {t: sum(t in set(d) for d in toks) for t in q}
    scores = []
    for d in toks:
        tf, dl, s = {}, len(d), 0.0
        for t in d:
            tf[t] = tf.get(t, 0) + 1
        for t in q:
            if tf.get(t):
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * tf[t] * (BM25_K1 + 1) / (tf[t] + BM25_K1 * (1 - BM25_B + BM25_B * dl / avg))
        scores.append(s)
    return scores


def bm25_select(instruction: str, skill_list: list[dict], k: int = K_SCOPED) -> list[dict]:
    """Top k skills by BM25 over the full SKILL.md text; ties by path. Fewer than k skills: all of them."""
    scores = bm25_scores(instruction, [s["text"] for s in skill_list])
    ranked = sorted(zip(scores, skill_list), key=lambda x: (-x[0], x[1]["rel"]))
    return [dict(s, score=round(sc, 4)) for sc, s in ranked[:k]]


def categorize(skill: dict) -> str:
    words = tokens(f"{skill['name']} {skill['description']}")
    best, hits = FALLBACK_CATEGORY, 0
    for cat, (_, keys) in CATEGORIES.items():
        n = sum(w in keys for w in words)
        if n > hits:
            best, hits = cat, n
    return best


def cue_terms(text: str) -> frozenset[str]:
    return frozenset(t for t in tokens(text, 4) if t not in STOP)


def cue_match(call_text: str, skill_terms: dict[str, frozenset[str]], fired: set[str]) -> list[str]:
    """Skill keys (sorted) that fire for one tool call: not fired yet, and >= CUE_MIN_SHARED shared terms."""
    seen = cue_terms(call_text)
    return sorted(k for k, terms in skill_terms.items() if k not in fired and len(seen & terms) >= CUE_MIN_SHARED)
