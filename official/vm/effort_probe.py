"""Does the local server act on the effort each harness requests? (rules.md: "Confirm requested reasoning effort reaches
actual model calls"; open since D106 for the main study, and new for Codex and Claude Code.) Counts only.

One fixed reasoning prompt, REPEATS calls per setting, straight to Ollama (not through the relay, so serving-check
logs are untouched). Settings are what the harnesses send: Hermes "xhigh" (its map of the requested "max" for an
unrecognised model; preregistration-cluster2.md) and Codex "max" on the Responses API; for Claude Code's Messages API,
both forms an effort can take there (an extended-thinking budget, and output_config.effort). Which of the two Claude
Code 2.1.284 sends is not known from here (the relay logs no bodies), so those rows are informational.
"low" / no thinking is the reference. Reports HTTP status, reasoning size and time per setting. Exit 1 if a Responses
setting that Hermes or Codex sends is rejected (non-200), since that harness's calls would fail; otherwise 0.
More reasoning at higher effort is reported, not required.

    python3 official/vm/effort_probe.py <ollama port> <model>
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

PROMPT = ("How many positive integers below 1000 are divisible by 7 or by 11 but not by both? "
          "Reason it through, then give the number alone on the last line.")
REPEATS = 2
MAX_OUT = 6000
RESPONSES = [("low", "reference"), ("xhigh", "Hermes"), ("max", "Codex")]
MESSAGES = [("none", "reference", {}),
            ("thinking-16k", "Claude Code (if it sends a thinking budget)", {"thinking": {"type": "enabled", "budget_tokens": 16000}}),
            ("effort-max", "Claude Code (if it sends output_config.effort)", {"output_config": {"effort": "max"}})]


def post(port: int, path: str, body: dict, headers: dict | None = None) -> tuple[int, dict, float]:
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            return r.status, json.loads(r.read()), time.monotonic() - t0
    except urllib.error.HTTPError as e:
        return e.code, {}, time.monotonic() - t0


def responses_reasoning(doc: dict) -> int:
    """Reasoning tokens reported, else reasoning text length / 4."""
    n = ((doc.get("usage") or {}).get("output_tokens_details") or {}).get("reasoning_tokens")
    if n:
        return int(n)
    text = "".join(c.get("text", "") for item in doc.get("output", []) if item.get("type") == "reasoning"
                   for c in (item.get("content") or []) + (item.get("summary") or []) if isinstance(c, dict))
    return len(text) // 4


def messages_reasoning(doc: dict) -> int:
    return sum(len(b.get("thinking", "")) for b in doc.get("content", []) if b.get("type") == "thinking") // 4


def run(port: int, model: str) -> list[dict]:
    rows = []
    for effort, who in RESPONSES:
        for _ in range(REPEATS):
            status, doc, dt = post(port, "/v1/responses", {"model": model, "input": PROMPT, "max_output_tokens": MAX_OUT,
                                                           "reasoning": {"effort": effort}})
            rows.append({"api": "responses", "setting": effort, "used_by": who, "status": status,
                         "reasoning": responses_reasoning(doc) if status == 200 else None, "seconds": round(dt, 1)})
    for name, who, extra in MESSAGES:
        for _ in range(REPEATS):
            status, doc, dt = post(port, "/v1/messages", {"model": model, "max_tokens": MAX_OUT + 16000,
                                                          "messages": [{"role": "user", "content": PROMPT}], **extra},
                                   {"x-api-key": "local-placeholder", "anthropic-version": "2023-06-01"})
            rows.append({"api": "messages", "setting": name, "used_by": who, "status": status,
                         "reasoning": messages_reasoning(doc) if status == 200 else None, "seconds": round(dt, 1)})
    return rows


def summarize(rows: list[dict]) -> tuple[list[str], bool]:
    lines, rejected = [], False
    for key in dict.fromkeys((r["api"], r["setting"]) for r in rows):
        group = [r for r in rows if (r["api"], r["setting"]) == key]
        ok = [r["reasoning"] for r in group if r["status"] == 200]
        statuses = sorted({r["status"] for r in group})
        rejected |= key[0] == "responses" and group[0]["used_by"] != "reference" and statuses != [200]
        lines.append(f"EFFORT_PROBE api={key[0]} setting={key[1]} used_by={group[0]['used_by']!r} status={statuses} "
                     f"reasoning_mean={round(sum(ok) / len(ok)) if ok else None} seconds_mean="
                     f"{round(sum(r['seconds'] for r in group) / len(group), 1)}")
    return lines, rejected


def main(argv: list[str]) -> int:
    rows = run(int(argv[1]), argv[2])
    lines, rejected = summarize(rows)
    print("\n".join(lines))
    print("EFFORT_PROBE_REJECTED: a setting a harness sends was refused" if rejected else "EFFORT_PROBE_DONE")
    return 1 if rejected else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
