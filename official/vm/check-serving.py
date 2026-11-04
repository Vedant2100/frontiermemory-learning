"""Serving checks for one stretch of a run (gate or set), from the host logs. Counts only.
Fails on any client abort or HTTP 5xx in the Ollama log, or any relay upstream error, max-wait drop or client close.
One exception (D99): a client close is expected, not a fault, when it happens as a trial's agent stops. Hermes starts its
post-turn background memory review on a daemon thread; when the agent process exits, that call is cut. Such a close is
excused only if the relay had not committed (no keepalive, so not a proxy cut), the upstream answered 200, and some trial's
agent_finished (results/official/summary-*.jsonl) falls 2 s before to 10 s after the close. Every other close still fails.
Retries (D100): when the relay cancels a call that a byte-identical retry superseded, Ollama logs that as a client abort.
Aborts up to the number of superseded calls are those cancels; any abort beyond them fails. Superseded calls are reported.

    python3 check-serving.py <ollama log dir> <server.log start line> <relay.log start line> [--need-keepalive] [--summaries DIR]
"""
import datetime as dt, glob, json, os, re, sys

olog, s0, r0 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
bad = []
server = open(f"{olog}/server.log", errors="replace").read().splitlines()[s0:]
aborts = sum("client closing the connection" in l for l in server)
s5xx = sum(bool(re.search(r"\|\s*5\d\d\s*\|", l)) for l in server)
print(f"ollama: {len(server)} new lines, {aborts} client aborts, {s5xx} HTTP 5xx")
relay = [json.loads(l) for l in open(f"{olog}/relay.log").read().splitlines()[r0:]]
superseded = sum(bool(r.get("superseded")) for r in relay)
print(f"relay: {superseded} calls superseded by an identical retry and cancelled (D100)")
bad += ["client aborts"] * (aborts > superseded) + ["HTTP 5xx"] * bool(s5xx)
posts = [r for r in relay if r["method"] == "POST"]
c = {k: sum(bool(r.get(k)) for r in relay) for k in ("committed", "upstream_error", "max_wait_drop", "client_closed")}
ka = sum(r.get("keepalives", 0) for r in relay)
longest = max((r.get("wait_s") or 0 for r in posts), default=0)
print(f"relay: {len(relay)} requests ({len(posts)} POST), {c['committed']} kept alive, {ka} keepalives, longest wait {longest}s, "
      f"{c['upstream_error']} upstream errors, {c['max_wait_drop']} max-wait drops, {c['client_closed']} client closes")
bad += ["no relay traffic"] * (not posts)
bad += ["no keepalive used"] * ("--need-keepalive" in sys.argv and not ka)
summ = sys.argv[sys.argv.index("--summaries") + 1] if "--summaries" in sys.argv else \
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "results", "official")
ends = []
for f in glob.glob(f"{summ}/summary-*.jsonl"):
    for l in open(f):
        a = json.loads(l).get("agent_finished")
        if a: ends.append(dt.datetime.fromisoformat(a.replace("Z", "+00:00")).timestamp())
year = dt.date.today().year
def at_agent_end(r):  # relay "t" is the request start in local time, 1 s resolution
    if r.get("committed") or r.get("upstream_status") != 200: return False
    t = dt.datetime.strptime(f"{year}-{r['t']}", "%Y-%m-%d %H:%M:%S").timestamp() + r.get("total_s", 0)
    return any(-2 <= e - t <= 10 for e in ends)
closes = [r for r in relay if r.get("client_closed")]
excused = sum(map(at_agent_end, closes))
print(f"relay: {excused} of {len(closes)} client closes at an agent's end (expected: background review cut, D99)")
c["client_closed"] = len(closes) - excused
bad += [k for k in ("upstream_error", "max_wait_drop", "client_closed") if c[k]]
print("SERVING:", "ok" if not bad else "FAIL: " + "; ".join(bad))
sys.exit(1 if bad else 0)
