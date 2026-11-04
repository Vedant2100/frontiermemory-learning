"""Serving checks for one stretch of a run (gate or set), from the host logs. Counts only.
Fails on any client abort or HTTP 5xx in the Ollama log, or any relay upstream error, max-wait drop or client close.

    python3 check-serving.py <ollama log dir> <server.log start line> <relay.log start line> [--need-keepalive]
"""
import json, re, sys

olog, s0, r0 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
bad = []
server = open(f"{olog}/server.log", errors="replace").read().splitlines()[s0:]
aborts = sum("client closing the connection" in l for l in server)
s5xx = sum(bool(re.search(r"\|\s*5\d\d\s*\|", l)) for l in server)
print(f"ollama: {len(server)} new lines, {aborts} client aborts, {s5xx} HTTP 5xx")
bad += ["client aborts"] * bool(aborts) + ["HTTP 5xx"] * bool(s5xx)
relay = [json.loads(l) for l in open(f"{olog}/relay.log").read().splitlines()[r0:]]
posts = [r for r in relay if r["method"] == "POST"]
c = {k: sum(bool(r.get(k)) for r in relay) for k in ("committed", "upstream_error", "max_wait_drop", "client_closed")}
ka = sum(r.get("keepalives", 0) for r in relay)
longest = max((r.get("wait_s") or 0 for r in posts), default=0)
print(f"relay: {len(relay)} requests ({len(posts)} POST), {c['committed']} kept alive, {ka} keepalives, longest wait {longest}s, "
      f"{c['upstream_error']} upstream errors, {c['max_wait_drop']} max-wait drops, {c['client_closed']} client closes")
bad += ["no relay traffic"] * (not posts)
bad += ["no keepalive used"] * ("--need-keepalive" in sys.argv and not ka)
bad += [k for k in ("upstream_error", "max_wait_drop", "client_closed") if c[k]]
print("SERVING:", "ok" if not bad else "FAIL: " + "; ".join(bad))
sys.exit(1 if bad else 0)
