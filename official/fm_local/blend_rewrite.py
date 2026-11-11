"""Blend arm: rewrite every task's instruction once, with run 1's memory worked into it (results/preregistration-arms.md, B6).
Runs in the guest VM (standard library only) against the local model through the relay (FM_LOCAL_BASE_URL).

    python3 blend_rewrite.py <memory job dir> <tasks dir> <out map json> <out report json>

For each task: one call (temperature 0.2, seed 1) with blend_logic.PROMPT, which holds only the original instruction and the
memory, never tests or solutions. If the contract (blend_logic.contract_check) fails, one more call with seed 2. A task that fails
twice keeps its original instruction in the arm and is excluded from the comparison. The map is written after every task and a
rerun skips finished tasks, so the sample is never redrawn. The report holds counts, sizes and hashes only: the rewrites embed
text from the gated corpus and stay in the guest.
Exit codes: 0 done; 3 fewer than blend_logic.MIN_VALID_TASKS valid rewrites; 1 the model could not be reached.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blend_logic as B  # noqa: E402

TEXT_SUFFIXES = {".md", ".txt", ".py", ".json", ".yaml", ".yml", ".sh", ".toml", ".csv"}


def memory_dir(job: str) -> str:
    if os.path.isfile(os.path.join(job, "MEMORY.md")):
        return job
    found = glob.glob(os.path.join(job, "*", "artifacts", "memory"))
    if len(found) != 1:
        raise SystemExit(f"expected one memory in {job}, found {len(found)}")
    return found[0]


def read_notes(mem: str) -> tuple[str, int]:
    parts, n = [], 0
    for root, _, files in sorted(os.walk(mem)):
        for f in sorted(files):
            if os.path.splitext(f)[1].lower() in TEXT_SUFFIXES:
                p = os.path.join(root, f)
                parts.append(f"--- {os.path.relpath(p, mem)} ---\n{open(p, errors='replace').read().strip()}")
                n += 1
    return "\n\n".join(parts), n


def chat(prompt: str, seed: int) -> str:
    base = os.environ["FM_LOCAL_BASE_URL"].rstrip("/")
    body = json.dumps({"model": B.MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": B.TEMPERATURE,
                       "seed": seed, "max_tokens": 16000, "stream": False}).encode()
    req = urllib.request.Request(f"{base}/chat/completions", data=body, headers={
        "Content-Type": "application/json", "Authorization": "Bearer local-placeholder"})
    with urllib.request.urlopen(req, timeout=3600) as r:
        data = json.loads(r.read().decode())
    choice = data["choices"][0]
    if choice.get("finish_reason") not in ("stop", None):
        raise RuntimeError(f"finish_reason {choice.get('finish_reason')}")
    return B.strip_thinking(choice["message"]["content"] or "")


def main(argv: list[str]) -> int:
    job, tasks, out, report_path = argv[1:5]
    notes, n_files = read_notes(memory_dir(job))
    notes_sha = hashlib.sha256(notes.encode()).hexdigest()
    done = json.load(open(out)) if os.path.isfile(out) else {}
    if done and done.get("_notes_sha256") not in (None, notes_sha):
        raise SystemExit("the memory changed since the rewrite; refusing to mix samples")
    done["_notes_sha256"], done["_prompt_sha256"] = notes_sha, B.PROMPT_SHA256
    for task in sorted(os.listdir(tasks)):
        path = os.path.join(tasks, task, "instruction.md")
        if not os.path.isfile(path) or task in done:
            continue
        original = open(path).read()
        entry = {"orig_sha": B.sha(original), "orig_chars": len(original.strip()), "blend": None, "ok": False, "rolls": 0,
                 "problems": []}
        for seed in B.SEEDS:
            entry["rolls"] += 1
            try:
                text = chat(B.build_prompt(original, notes), seed)
            except Exception as e:  # model unreachable or cut off: not a contract failure
                print(f"BLEND_MODEL_ERROR task={task} seed={seed} {type(e).__name__}: {str(e)[:100]}", flush=True)
                json.dump(done, open(out, "w"), indent=1)
                return 1
            problems = B.contract_check(original, text)
            entry["problems"] = problems
            if not problems:
                entry.update(blend=text, ok=True, blend_sha=B.sha(text), blend_chars=len(text),
                             added_sentences=B.added_sentences(original, text))
                break
        done[task] = entry
        json.dump(done, open(out, "w"), indent=1)
        print(f"BLEND task={task} ok={entry['ok']} rolls={entry['rolls']} added_sentences={entry.get('added_sentences', 0)} "
              f"orig_chars={entry['orig_chars']} blend_chars={entry.get('blend_chars', 0)}", flush=True)
    entries = {k: v for k, v in done.items() if not k.startswith("_")}
    ok = sum(v["ok"] for v in entries.values())
    report = {"tasks": len(entries), "valid": ok, "failed": [k for k, v in entries.items() if not v["ok"]],
              "memory_files": n_files, "notes_sha256": notes_sha, "prompt_sha256": B.PROMPT_SHA256,
              "per_task": {k: {x: v.get(x) for x in ("ok", "rolls", "orig_sha", "blend_sha", "orig_chars", "blend_chars",
                                                     "added_sentences")} for k, v in entries.items()}}
    json.dump(report, open(report_path, "w"), indent=1)
    print(f"BLEND_REWRITE: done tasks={len(entries)} valid={ok} failed={len(entries) - ok}", flush=True)
    if ok < B.MIN_VALID_TASKS:
        print(f"BLEND_REWRITE: TOO_FEW_VALID ({ok} < {B.MIN_VALID_TASKS})", flush=True)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
