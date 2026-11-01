#!/usr/bin/env python3
"""Scope leakage: do memory trials that touch other-family topics fare worse?

Descriptive analysis (prereg v1: "Scope-leakage analysis" paragraph, Amendment A4 item 3,
Amendment A5 for cases_lb). For each memory trial it records:
  - the same-family / other-family topic entries in the visible window of MEMORY.md
    (the first and last 5000 characters, via memory_exposure.visible);
  - the topic files the agent opened (read commands on topics/<slug>.md that exist);
  - whether the agent searched MEMORY.md / memory_summary.
Family rule: a topic is same-family for a task iff name_tokens(topic slug) and
name_tokens(task name) share a token. Only names are used, never task content.
A memory trial is "harmful" if its cases_lb is below the A0 mean cases_lb of its task
(and, as a second flag, if its strict reward is below the A0 mean strict reward).

Prints counts only. Topic slugs appear only in the optional --details file (local).
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from memory_exposure import SLUG, name_tokens, visible  # noqa: E402

ARM_MEMORY = {
    "R25": os.path.join(ROOT, "memory", "frozen-r25"),
    "M3": os.path.join(ROOT, "memory", "frozen-v5-fullindex"),
}
READ_VERB = re.compile(r"\b(cat|sed|head|tail|less|more|grep|rg|awk|wc|nl|bat)\b")
TOPIC_PATH = re.compile(r"topics/(g\d{3}-[a-z0-9-]+)\.md")
MEMORY_REF = re.compile(r"MEMORY\.md|memory_summary", re.I)


def same_family(slug, task):
    return bool(name_tokens(slug) & name_tokens(task))


def cases_lb(passed, collected, total):
    """Amendment A5 lower bound: passed minus collected tests beyond the original cases."""
    return max(0, passed - max(0, collected - total))


def visible_slugs(memory_dir):
    src = open(os.path.join(memory_dir, "MEMORY.md"), encoding="utf-8").read()
    all_slugs = set(SLUG.findall(src))
    return set(SLUG.findall(visible(src))) & all_slugs


def existing_topics(memory_dir):
    names = os.listdir(os.path.join(memory_dir, "topics"))
    return {n[:-3] for n in names if n.endswith(".md") and SLUG.fullmatch(n[:-3])}


def analyze_commands(cmds, topics_present):
    """Return (opened_slugs, searched_memory_md) from shell command strings."""
    opened, searched = set(), False
    for cmd in cmds:
        if MEMORY_REF.search(cmd):
            searched = True
        if READ_VERB.search(cmd):
            for slug in TOPIC_PATH.findall(cmd):
                if slug in topics_present:
                    opened.add(slug)
    return opened, searched


def read_commands(events_path):
    by_id = {}
    with open(events_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            it = e.get("item") or {}
            if it.get("type") == "command_execution":
                key = it.get("id") or ("anon", len(by_id))
                by_id[key] = it.get("command") or ""
    return list(by_id.values())


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def self_check():
    # Family rule
    assert same_family("g001-awilix-di", "awilix-release-tier-implicit")
    assert same_family("g003-word2vec-tokenize", "build-word2vec-pipeline")
    assert not same_family("g002-cookie-store", "build-word2vec-pipeline")
    assert not same_family("g004-tier-rules", "awilix-release-tier-implicit")  # "tier" is a stop word
    assert not same_family("g005-ab-x", "build-word2vec-pipeline")  # tokens of length <= 2 ignored
    # cases_lb (Amendment A5)
    assert cases_lb(5, 8, 6) == 3
    assert cases_lb(4, 6, 6) == 4
    assert cases_lb(6, 4, 6) == 6  # fewer collected than total: no penalty
    assert cases_lb(2, 10, 6) == 0  # floored at zero
    assert cases_lb(6, 6, 6) == 6
    assert cases_lb(0, 0, 0) == 0
    # visible window: first and last 5000 characters, short sources unchanged
    assert visible("a" * 100) == "a" * 100
    assert len(visible("a" * 12000)) == 10001
    # opened-file rule on synthetic commands
    topics = {"g001-awilix-di", "g002-cookie-x"}
    cmds = [
        "/bin/bash -lc 'cat /codex-home/memories/topics/g001-awilix-di.md'",  # opened
        "/bin/bash -lc 'grep -n g001 /codex-home/memories/MEMORY.md'",  # searched MEMORY.md only
        "/bin/bash -lc 'ls /codex-home/memories/topics/g002-cookie-x.md'",  # no read verb
        "/bin/bash -lc 'cat /codex-home/memories/topics/g009-missing.md'",  # file absent
    ]
    opened, searched = analyze_commands(cmds, topics)
    assert opened == {"g001-awilix-di"}, opened
    assert searched
    opened, searched = analyze_commands(["ls /tmp"], topics)
    assert opened == set() and not searched
    print("self-check: ok", file=sys.stderr)


def load_run(run_dir):
    task = open(os.path.join(run_dir, "task.txt"), encoding="utf-8").read().strip().splitlines()[0]
    trials, excluded, missing_events = [], 0, 0
    topics_cache = {}
    for d in sorted(glob.glob(os.path.join(run_dir, "trial-*-*"))):
        rec_path = os.path.join(d, "trial-record.json")
        if not os.path.isdir(d) or not os.path.exists(rec_path):
            continue
        rec = json.load(open(rec_path, encoding="utf-8"))
        if rec.get("valid") is False:
            excluded += 1  # infrastructure failure: not scored (prereg section 3)
            continue
        arm = rec.get("arm") or d.rsplit("-", 1)[-1]
        passed, total, collected = rec.get("cases_passed"), rec.get("cases_total"), rec.get("verifier_collected")
        lb = cases_lb(passed, collected or 0, total) if None not in (passed, total) else None
        ev = os.path.join(d, "events.jsonl")
        has_events = os.path.exists(ev)
        missing_events += not has_events
        cmds = read_commands(ev) if has_events else []
        if arm in ARM_MEMORY:
            mdir = ARM_MEMORY[arm]
            if mdir not in topics_cache:
                topics_cache[mdir] = (visible_slugs(mdir), existing_topics(mdir))
            vis, topics = topics_cache[mdir]
        else:
            vis, topics = set(), set()
        opened, searched = analyze_commands(cmds, topics)
        trials.append({
            "job_id": rec.get("job_id"), "trial": os.path.basename(d), "arm": arm, "task": task,
            "strict": rec.get("strict_reward"), "passed": passed, "lb": lb,
            "vis_same": sorted(s for s in vis if same_family(s, task)),
            "vis_other": sorted(s for s in vis if not same_family(s, task)),
            "opened_same": sorted(s for s in opened if same_family(s, task)),
            "opened_other": sorted(s for s in opened if not same_family(s, task)),
            "searched": searched, "events_present": has_events,
        })
    return task, trials, excluded, missing_events


def summarize(task, trials):
    a0 = [t for t in trials if t["arm"] == "A0"]
    a0_lb = mean([t["lb"] for t in a0 if t["lb"] is not None])
    a0_strict = mean([t["strict"] for t in a0 if t["strict"] is not None])
    out = {"a0_n": len(a0), "a0_mean_cases_lb": a0_lb, "a0_mean_strict": a0_strict, "arms": {}}
    for arm in sorted({t["arm"] for t in trials}):
        ts = [t for t in trials if t["arm"] == arm]
        consulted = [t for t in ts if t["opened_same"] or t["opened_other"] or t["searched"]]
        row = {
            "n_trials": len(ts),
            "n_consulted": len(consulted),
            "n_searched_memory_md": sum(t["searched"] for t in ts),
            "visible_same": len(ts[0]["vis_same"]) if ts else 0,
            "visible_other": len(ts[0]["vis_other"]) if ts else 0,
            "mean_opened_same": mean([len(t["opened_same"]) for t in ts]),
            "mean_opened_other": mean([len(t["opened_other"]) for t in ts]),
            "mean_strict": mean([t["strict"] for t in ts if t["strict"] is not None]),
            "mean_cases_lb": mean([t["lb"] for t in ts if t["lb"] is not None]),
        }
        if arm != "A0" and a0_lb is not None and a0_strict is not None:
            for flag, test in (
                ("harmful_lb", lambda t: t["lb"] is not None and t["lb"] < a0_lb),
                ("harmful_strict", lambda t: t["strict"] is not None and t["strict"] < a0_strict),
            ):
                harm = [t for t in ts if test(t)]
                ok = [t for t in ts if not test(t) and (t["lb"] if flag == "harmful_lb" else t["strict"]) is not None]
                row[flag] = len(harm)
                row[flag + "_opened_other"] = sum(bool(t["opened_other"]) for t in harm)
                row[flag + "_nonharmful"] = len(ok)
                row[flag + "_nonharmful_opened_other"] = sum(bool(t["opened_other"]) for t in ok)
        out["arms"][arm] = row
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", action="append", default=[], help="job dir with task.txt and trial-*-ARM/ (repeatable)")
    ap.add_argument("--details", help="write per-trial topic slug lists to this local JSON (never stdout)")
    ap.add_argument("--self-check", action="store_true", help="assert the family rule and lb formula, then exit")
    a = ap.parse_args()
    if a.self_check:
        self_check()
        return
    if not a.run_dir:
        ap.error("--run-dir is required unless --self-check is given")

    by_task = defaultdict(list)
    jobs = defaultdict(set)
    excluded_total = missing_total = 0
    for rd in a.run_dir:
        task, trials, excluded, missing = load_run(rd)
        by_task[task].extend(trials)
        excluded_total += excluded
        missing_total += missing
        jobs[task].update(str(t["job_id"]) for t in trials)

    report = {
        "method": "prereg v1: Scope-leakage analysis; A4 item 3; A5 cases_lb; counts only",
        "excluded_invalid_trials": excluded_total,
        "trials_missing_events": missing_total,
        "tasks": {},
    }
    details = []
    for task in sorted(by_task):
        s = summarize(task, by_task[task])
        s["job_ids"] = sorted(jobs[task])
        report["tasks"][task] = s
        for t in by_task[task]:
            details.append({k: t[k] for k in ("task", "job_id", "trial", "arm", "vis_same", "vis_other",
                                              "opened_same", "opened_other", "searched")})
    if a.details:
        with open(a.details, "w", encoding="utf-8") as f:
            json.dump(details, f, indent=1)
    json.dump(report, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
