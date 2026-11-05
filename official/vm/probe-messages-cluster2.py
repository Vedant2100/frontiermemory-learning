#!/usr/bin/env python3
"""Count-only preflight for Ollama's Anthropic Messages tool and streaming support."""
from __future__ import annotations

import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def payload(model: str, *, stream: bool) -> dict:
    return {
        "model": model,
        "max_tokens": 64,
        "stream": stream,
        "messages": [{"role": "user", "content": "Call probe_tool once with value equal to ok."}],
        "tools": [{
            "name": "probe_tool",
            "description": "A local compatibility probe; do not access external services.",
            "input_schema": {
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
        }],
        "tool_choice": {"type": "tool", "name": "probe_tool"},
    }


def open_request(url: str, model: str, *, stream: bool):
    request = Request(
        url,
        data=json.dumps(payload(model, stream=stream)).encode(),
        headers={
            "Content-Type": "application/json",
            "x-api-key": "local-placeholder",
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    return urlopen(request, timeout=900)


def nonstream_check(url: str, model: str) -> bool:
    with open_request(url, model, stream=False) as response:
        data = json.loads(response.read())
    return response.status == 200 and any(
        block.get("type") == "tool_use" and block.get("name") == "probe_tool"
        for block in data.get("content", []) if isinstance(block, dict)
    )


def stream_check(url: str, model: str) -> tuple[bool, int, int]:
    event_count = 0
    tool_starts = 0
    stopped = False
    with open_request(url, model, stream=True) as response:
        if response.status != 200:
            return False, event_count, tool_starts
        for raw in response:
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if not data or data == "[DONE]":
                continue
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            event_count += 1
            if event.get("type") == "content_block_start":
                block = event.get("content_block") or {}
                tool_starts += int(block.get("type") == "tool_use" and block.get("name") == "probe_tool")
            stopped |= event.get("type") == "message_stop"
    return tool_starts > 0 and stopped, event_count, tool_starts


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: probe-messages-cluster2.py RELAY_V1_URL MODEL")
        return 2
    base, model = sys.argv[1:]
    url = base.rstrip("/") + "/messages"
    try:
        nonstream_ok = nonstream_check(url, model)
        stream_ok, event_count, tool_starts = stream_check(url, model)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError):
        print("CLAUDE_MESSAGES_PREFLIGHT_FAILED request_or_protocol_error")
        return 1
    print(
        "CLAUDE_MESSAGES_PREFLIGHT "
        f"nonstream_tool_use={int(nonstream_ok)} stream_tool_use={int(stream_ok)} "
        f"stream_events={event_count} stream_tool_starts={tool_starts}"
    )
    return 0 if nonstream_ok and stream_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
