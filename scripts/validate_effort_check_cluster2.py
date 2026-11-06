#!/usr/bin/env python3
"""Fail-closed check for the required uncounted low/xhigh Ollama effort receipt."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

EXPECTED_MODEL = "qwen3.8:27b-mtp-q4_K_M"


def nonnegative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("results/effort-check-cluster2.json")
    try:
        receipt = json.loads(path.read_text())
        calls = receipt.get("calls")
        valid = (
            receipt.get("status") == "pass"
            and receipt.get("source") == "local_ollama_openai_responses"
            and receipt.get("endpoint_path") == "/v1/responses"
            and receipt.get("via_relay") is False
            and receipt.get("model") == EXPECTED_MODEL
            and re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("prompt_sha256", ""))) is not None
            and receipt.get("repeats_per_effort") == 3
            and receipt.get("request_controls") == {"max_output_tokens": 1024, "temperature": 0.6}
            and isinstance(calls, list)
            and len(calls) == 6
        )
        if not valid:
            raise ValueError("receipt metadata does not match the required six direct Responses calls")
        efforts = {effort: [] for effort in ("low", "xhigh")}
        repeats = {effort: set() for effort in efforts}
        for call in calls:
            effort = call.get("requested_effort")
            if effort not in efforts or call.get("http_status") != 200:
                raise ValueError("call effort or HTTP status is invalid")
            if call.get("repeat") not in (1, 2, 3) or call["repeat"] in repeats[effort]:
                raise ValueError("call repeat index is missing, duplicated, or out of range")
            repeats[effort].add(call["repeat"])
            if not nonnegative_int(call.get("output_tokens")) or not nonnegative_int(call.get("output_text_chars")):
                raise ValueError("output token/character counts are invalid")
            reasoning = call.get("reasoning_tokens")
            if reasoning is not None and not nonnegative_int(reasoning):
                raise ValueError("reasoning token count is invalid")
            reasoning_chars = call.get("reasoning_summary_chars")
            if reasoning_chars is not None and not nonnegative_int(reasoning_chars):
                raise ValueError("reasoning summary length is invalid")
            efforts[effort].append(call)
        if any(len(efforts[effort]) != 3 or repeats[effort] != {1, 2, 3} for effort in efforts):
            raise ValueError("expected three calls at both low and xhigh effort")
        summary = receipt.get("comparison")
        if not isinstance(summary, dict) or any(effort not in summary for effort in efforts):
            raise ValueError("per-effort comparison summary is missing")
        for effort in efforts:
            expected = {
                "reasoning_tokens": [call.get("reasoning_tokens") for call in efforts[effort]],
                "output_tokens": [call["output_tokens"] for call in efforts[effort]],
                "output_text_chars": [call["output_text_chars"] for call in efforts[effort]],
                "reasoning_summary_chars": [call.get("reasoning_summary_chars") for call in efforts[effort]],
            }
            if summary[effort] != expected:
                raise ValueError(f"{effort} comparison summary differs from individual calls")
        receipt["prompt_sha256"]  # required above; never print prompt content
    except (OSError, ValueError, TypeError, json.JSONDecodeError, AttributeError) as exc:
        print(f"EFFORT_CHECK_FAILED: {exc}")
        return 1
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"EFFORT_CHECK_OK calls=6 prompt_sha256={receipt['prompt_sha256']} receipt_sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
