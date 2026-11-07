"""Stand-in model server for check (a), D128: records, for each POST, whether given marker strings appear in the request's
system text (Responses `instructions` and system/developer input items; Chat `system`/`developer` messages), then answers
400 so the client stops. Prints nothing; writes one JSON line per request to the log. Standard library only.

    python3 capture_server.py <port> <log.jsonl> <marker> [<marker> ...]
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, LOG, MARKERS = int(sys.argv[1]), sys.argv[2], sys.argv[3:]


def system_text(body: dict) -> str:
    parts = []
    if isinstance(body.get("instructions"), str):
        parts.append(body["instructions"])
    for item in (body.get("input") if isinstance(body.get("input"), list) else []) + (body.get("messages") or []):
        if isinstance(item, dict) and item.get("role") in ("system", "developer"):
            c = item.get("content")
            if isinstance(c, str):
                parts.append(c)
            elif isinstance(c, list):
                parts += [x.get("text", "") for x in c if isinstance(x, dict)]
    if isinstance(body.get("system"), str):
        parts.append(body["system"])
    return "\n".join(parts)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(200, {"object": "list", "data": [{"id": "qwen3.8:27b-mtp-q4_K_M", "object": "model"}]})

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            body = json.loads(raw)
        except ValueError:
            body = {}
        st = system_text(body)
        rec = {"path": self.path, "system_chars": len(st),
               "in_system": {m[:24]: m in st for m in MARKERS},
               "in_body": {m[:24]: json.dumps(m)[1:-1] in raw.decode("utf-8", "replace") or m in raw.decode("utf-8", "replace") for m in MARKERS}}
        with open(LOG, "a") as f:
            f.write(json.dumps(rec) + "\n")
        self._send(400, {"error": {"message": "capture test: request recorded", "type": "invalid_request_error"}})


ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
