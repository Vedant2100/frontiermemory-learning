"""Blend arm (results/preregistration-arms.md, B6): the rules for rewriting a task description so that run 1's memory is part
of it. Standard library only; used by blend_rewrite.py (guest), blend_hermes.py, blend_check.py and the tests.

The rewrite is checked by a contract: every concrete item of the original (backticked spans, paths, file names, snake_case and
CamelCase identifiers, flags, numbers) must appear verbatim in the rewrite, the rewrite must not talk about notes, memory or
earlier runs unless the original does, it must not be shorter than the original, and it must not start with a preface.
"""

from __future__ import annotations

import hashlib
import re

MODEL = "qwen3.8:27b-mtp-q4_K_M"
TEMPERATURE = 0.2
SEEDS = (1, 2)  # one sample; one automatic re-roll if the contract fails
MIN_VALID_TASKS = 10  # fewer valid rewrites than this and the arm's trials are not run

PROMPT = """You are editing a task description for an AI coding agent.

Below are NOTES (knowledge distilled from earlier work on similar tasks) and the ORIGINAL TASK DESCRIPTION.

Rewrite the task description so that whatever in the notes is useful for THIS task becomes part of the task description itself: ordinary background, conventions, pitfalls and checks, written as part of the task and not as advice from someone else. Keep every requirement, path, file name, command, number, time limit and output format of the original exactly as written. Do not remove or weaken anything. Do not mention notes, memory, earlier runs, earlier attempts or lessons. Do not add facts that appear in neither text. If the notes hold nothing useful for this task, return the original description unchanged.

Output only the rewritten task description, with no preface.

=== NOTES ===
{notes}

=== ORIGINAL TASK DESCRIPTION ===
{instruction}
"""
PROMPT_SHA256 = hashlib.sha256(PROMPT.encode()).hexdigest()

BACKTICK = re.compile(r"`([^`\n]+)`")
PATH = re.compile(r"(?<![\w/.])(?:~|\.{1,2})?/(?:[\w.\-@+]+/)*[\w.\-@+]+")
FILE = re.compile(r"\b[\w\-]+(?:\.[A-Za-z0-9]{1,6})+\b")
SNAKE = re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b")
CAMEL = re.compile(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+\b")
FLAG = re.compile(r"(?<![\w-])--?[A-Za-z][\w\-]*")
NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?:%|\s?(?:s|sec|seconds|min|minutes|ms|KB|MB|GB|h|hours))?")
LIST_MARKER = re.compile(r"^\s*\d+[.)]\s+", re.M)
FORBIDDEN = re.compile(r"\b(notes?|memory|memories|(?:earlier|previous|past|prior) (?:runs?|attempts?|sessions?|work)|lessons?|"
                       r"learned|skills?)\b", re.I)
PREFACE = re.compile(r"^\W*(here is|here's|sure|certainly|rewritten|below is|of course)\b", re.I)
THINK = re.compile(r"<think>.*?</think>", re.S)


def sha(text: str) -> str:
    return hashlib.sha256(text.strip().encode()).hexdigest()


def strip_thinking(text: str) -> str:
    return THINK.sub("", text).strip()


def required_items(original: str) -> list[str]:
    body = LIST_MARKER.sub("", original)
    items: set[str] = set()
    for rx in (BACKTICK, PATH, FILE, SNAKE, CAMEL, FLAG, NUMBER):
        for m in rx.finditer(body):
            item = (m.group(1) if rx is BACKTICK else m.group(0)).strip().rstrip(".,;:")
            if item:
                items.add(item)
    return sorted(items)


def contract_check(original: str, rewrite: str) -> list[str]:
    """Problems with a rewrite; empty if it keeps the contract."""
    problems = []
    if not rewrite.strip():
        return ["empty rewrite"]
    if PREFACE.match(rewrite):
        problems.append("starts with a preface")
    missing = [i for i in required_items(original) if i not in rewrite]
    if missing:
        problems.append(f"{len(missing)} item(s) of the original missing: " + ", ".join(repr(m) for m in missing[:8]))
    seen = {m.group(0).lower() for m in FORBIDDEN.finditer(original)}
    talk = sorted({m.group(0).lower() for m in FORBIDDEN.finditer(rewrite)} - seen)
    if talk:
        problems.append("mentions " + ", ".join(talk))
    if len(rewrite.strip()) < len(original.strip()):
        problems.append("shorter than the original")
    return problems


def sentences(text: str) -> set[str]:
    return {re.sub(r"\s+", " ", s).strip().lower() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()}


def added_sentences(original: str, rewrite: str) -> int:
    return len(sentences(rewrite) - sentences(original))


def build_prompt(instruction: str, notes: str) -> str:
    return PROMPT.format(notes=notes, instruction=instruction.strip())
