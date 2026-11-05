"""Relay between the Docker guest and Ollama, so Harbor's egress proxy never cuts a slow model call.

Harbor's no-network sidecar drops any response whose first byte hasn't arrived within 15 s (measured, D93).
Cloud APIs answer sooner; a local model reading a long prompt or waiting for its slot may not.

  - If Ollama answers within GRACE s, its status, headers and body pass through unchanged.
  - Otherwise the relay sends 200 at once and keeps the connection alive until Ollama answers:
      streaming request (JSON "stream": true): SSE comment lines ": keepalive", which SSE clients ignore;
      other requests: single spaces, which JSON parsers ignore.
    Then Ollama's body follows byte for byte. If Ollama then returns an error status or fails, the relay drops
    the connection without finishing the body, which the client sees as a connection error and may retry, as it
    would a 5xx. (A 200 can't carry an error the OpenAI SDK understands for non-streaming calls.)
  - A call still unanswered after MAX_WAIT is dropped the same way, so the client's own timeout still applies.
  - A retry supersedes its original (D100). When Hermes's watchdog cancels a call and retries, the cancel may not
    reach Ollama through the egress proxy, so the old call keeps the model busy and the retry queues behind it.
    A POST whose body is byte-identical to one still in flight is a retry: the relay closes the older call's
    upstream connection (Ollama stops it) and drops the older client connection. Different bodies never interact.
    Hermes's event-based watchdogs (no-event and idle) count parsed events, which keepalive comments are not.

Model output is untouched. The log has one JSON line per request with counts and timings only, never bodies.

    python3 model_relay.py <listen port> <ollama port> <log file>
"""

import hashlib
import http.client
import json
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

GRACE = 10.0     # below the proxy's 15 s first-byte cut
KEEPALIVE = 5.0  # interval while waiting after committing to 200
MAX_WAIT = 1800.0  # Hermes's per-call socket timeout (HERMES_API_TIMEOUT default). Keepalives would hide it,
                   # so a call unanswered this long is dropped, as the client's read timeout would drop it.
HOP = {"connection", "keep-alive", "transfer-encoding", "content-length", "proxy-connection", "upgrade", "te", "trailer"}


class Relay(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    upstream_port = 0
    log_lock = threading.Lock()
    log_file = None
    inflight_lock = threading.Lock()
    inflight = {}  # body digest -> (conn, rec) of the newest call with that body

    def log_message(self, *a):
        pass

    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass  # client dropped an idle keep-alive connection

    def _log(self, **rec):
        with self.log_lock:
            self.log_file.write(json.dumps(rec) + "\n")
            self.log_file.flush()

    def _chunk(self, data):
        if data:
            self.wfile.write(b"%x\r\n%s\r\n" % (len(data), data))
            self.wfile.flush()

    def _end(self):
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()

    def _relay(self):
        t0 = time.monotonic()
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else None
        stream = False
        if body:
            try:
                stream = json.loads(body).get("stream") is True
            except (ValueError, AttributeError):
                pass
        rec = {"t": time.strftime("%m-%d %H:%M:%S"), "method": self.command, "path": self.path.split("?")[0],
               "stream": stream, "committed": False, "keepalives": 0}

        conn = http.client.HTTPConnection("127.0.0.1", self.upstream_port, timeout=None)
        key = hashlib.sha256(body).hexdigest() if (self.command == "POST" and body) else None
        if key:
            rec["body_sha"] = key[:12]
            with self.inflight_lock:
                old = self.inflight.get(key)
                self.inflight[key] = (conn, rec)
            if old:
                old_conn, old_rec = old
                old_rec["superseded"] = True
                rec["supersedes"] = True
                try:
                    if old_conn.sock:
                        old_conn.sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        result, done = {}, threading.Event()

        def call():
            try:
                hdrs = {k: v for k, v in self.headers.items() if k.lower() not in HOP and k.lower() != "host"}
                conn.request(self.command, self.path, body=body, headers=hdrs)
                result["resp"] = conn.getresponse()
            except Exception as e:  # upstream unreachable or reset
                result["exc"] = f"{type(e).__name__}: {e}"
            done.set()

        threading.Thread(target=call, daemon=True).start()
        try:
            if not done.wait(GRACE):
                # Commit to 200 now, before the proxy's cut, and keep the line alive until Ollama answers.
                rec["committed"] = True
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream" if stream else "application/json")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                ka = b": keepalive\n\n" if stream else b" "
                self._chunk(ka)
                rec["keepalives"] += 1
                while not done.wait(KEEPALIVE):
                    if time.monotonic() - t0 > MAX_WAIT:
                        rec["max_wait_drop"] = True
                        self.close_connection = True
                        return
                    self._chunk(ka)
                    rec["keepalives"] += 1
            rec["wait_s"] = round(time.monotonic() - t0, 1)
            if rec.get("superseded"):
                self.close_connection = True  # a retry took over; this client already gave up
                return
            resp = result.get("resp")
            rec["upstream_status"] = resp.status if resp else None
            if resp is None or (rec["committed"] and resp.status != 200):
                rec["upstream_error"] = result.get("exc") or "status after commit"
                if rec["committed"]:
                    self.close_connection = True  # unfinished chunked body: a connection error for the client
                    return
                msg = json.dumps({"error": {"message": f"model relay: upstream failed: {result['exc']}",
                                            "type": "server_error", "code": 502}}).encode()
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(msg)))
                self.end_headers()
                self.wfile.write(msg)
                return
            if not rec["committed"]:
                self.send_response(resp.status, resp.reason)
                for k, v in resp.getheaders():
                    if k.lower() not in HOP:
                        self.send_header(k, v)
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
            nbytes = 0
            while True:
                try:
                    data = resp.read1(65536)
                except OSError:
                    if not rec.get("superseded"):
                        raise
                    data = b""
                if not data:
                    break
                nbytes += len(data)
                self._chunk(data)
            rec["bytes"] = nbytes
            if rec.get("superseded"):
                self.close_connection = True
                return
            self._end()
        except (BrokenPipeError, ConnectionResetError):
            rec["client_closed"] = True
        finally:
            conn.close()  # if the client left, this also tells Ollama to stop
            if key:
                with self.inflight_lock:
                    if self.inflight.get(key, (None,))[0] is conn:
                        del self.inflight[key]
            rec["total_s"] = round(time.monotonic() - t0, 1)
            self._log(**rec)

    do_GET = do_POST = do_PUT = do_DELETE = _relay


def main():
    listen, upstream, log_path = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    Relay.upstream_port = upstream
    Relay.log_file = open(log_path, "a")
    srv = ThreadingHTTPServer(("127.0.0.1", listen), Relay)
    srv.daemon_threads = True
    srv.serve_forever()


if __name__ == "__main__":
    main()
