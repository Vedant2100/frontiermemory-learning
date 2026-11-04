"""Dummy HTTP server for the slow-path test. Paths start /<kind>/<N>/ (anything after is ignored, so it can be an OpenAI base URL).
GET  /first/N: wait N s, then respond.   GET /idle/N: send headers and one byte, wait N s, then finish.
POST /first/N: wait N s, then a chat completion, streamed as SSE if the JSON body has "stream": true.
POST /err/N:   wait N s, then HTTP 500 with an OpenAI-style error body."""
import json, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CHUNK = {"id": "x", "object": "chat.completion.chunk", "created": 0, "model": "m",
         "choices": [{"index": 0, "delta": {"role": "assistant", "content": "ok"}, "finish_reason": None}]}
FULL = {"id": "x", "object": "chat.completion", "created": 0, "model": "m",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}

class H(BaseHTTPRequestHandler):
    def _send(self, code, ctype, body):
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        kind, n = self.path.strip("/").split("/")[:2]
        if kind == "first":
            time.sleep(int(n)); self._send(200, "text/plain", b"ok")
        else:
            self.send_response(200); self.send_header("Content-Length", "2"); self.end_headers(); self.wfile.write(b"o"); self.wfile.flush()
            time.sleep(int(n)); self.wfile.write(b"k")
    def do_POST(self):
        kind, n = self.path.strip("/").split("/")[:2]
        req = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        time.sleep(int(n))
        if kind == "err":
            return self._send(500, "application/json", json.dumps({"error": {"message": "slow-server test error", "type": "api_error"}}).encode())
        if req.get("stream"):
            body = b"".join(b"data: " + json.dumps(CHUNK).encode() + b"\n\n" for _ in range(2)) + b"data: [DONE]\n\n"
            return self._send(200, "text/event-stream", body)
        self._send(200, "application/json", json.dumps(FULL).encode())
    def log_message(self, *a): pass

ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
