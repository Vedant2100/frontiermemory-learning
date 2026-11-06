"""Serving checks for one stretch of a run (gate or set), from the host logs. Counts only.
Fails on any client abort or HTTP 5xx in the Ollama log, or any relay upstream error, max-wait drop or client close.
One exception (D99): a client close is expected, not a fault, when it happens as a trial's agent stops. Hermes starts its
post-turn background memory review on a daemon thread; when the agent process exits, that call is cut. Such a close is
excused only if the relay had not committed (no keepalive, so not a proxy cut), the upstream answered 200, and the call
started 1 s after to 10 s before some trial's agent_finished (results/official/summary-*.jsonl) and closed within 60 s
after it. The review starts as the final answer lands; the close comes when the container is torn down, which once took
18 s (D104), so the rule keys on the start. Every other close still fails.
Retries (D100): when the relay cancels a call that a byte-identical retry superseded, Ollama logs that as a client abort.
Aborts up to the number of superseded calls are those cancels; any abort beyond them fails. Superseded calls are reported.
Model tool-call parse errors (D107): when the model emits a malformed tool call, Ollama logs "tool call parsing failed" and
answers 500. That's model output, not serving. Such a 500 is excused only if the parse warning is in the 5 lines before it,
and the relay passed it through uncommitted and a byte-identical retry got 200 within 60 s. Every other 5xx still fails.
Cancel echoes (D112): when the relay cancels a superseded call, Ollama closes that request with a 500 (after an abort line if
it was running, without one if it was still queued). A 5xx logged within 3 s of a superseded call's end, one per superseded
call, is excused, and only while aborts don't exceed superseded calls either.

    python3 check-serving.py <ollama log dir> <server.log start line> <relay.log start line> [--need-keepalive] [--summaries DIR]
"""
import datetime as dt, glob, json, os, re, sys

olog, s0, r0 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
bad = []
server = open(f"{olog}/server.log", errors="replace").read().splitlines()[s0:]
aborts = sum("client closing the connection" in l for l in server)
i5xx = [i for i, l in enumerate(server) if re.search(r"\|\s*5\d\d\s*\|", l)]
parse5xx = sum(any("tool call parsing failed" in l for l in server[max(0, i - 5):i]) for i in i5xx)
print(f"ollama: {len(server)} new lines, {aborts} client aborts, {len(i5xx)} HTTP 5xx ({parse5xx} after a tool-call parse error)")
relay = [json.loads(l) for l in open(f"{olog}/relay.log").read().splitlines()[r0:]]
superseded = sum(bool(r.get("superseded")) for r in relay)
print(f"relay: {superseded} calls superseded by an identical retry and cancelled (D100)")
year0 = dt.date.today().year
def ts(r): return dt.datetime.strptime(f"{year0}-{r['t']}", "%Y-%m-%d %H:%M:%S").timestamp()
def recovered(i, r):  # an uncommitted 5xx answered, then a byte-identical retry got 200 within 60 s
    return not r.get("committed") and r.get("body_sha") and any(
        x.get("body_sha") == r["body_sha"] and x.get("upstream_status") == 200 and 0 <= ts(x) - ts(r) <= 60 for x in relay[i + 1:])
r5xx = [(i, r) for i, r in enumerate(relay) if (r.get("upstream_status") or 0) >= 500]
rec = sum(bool(recovered(i, r)) for i, r in r5xx)
print(f"relay: {len(r5xx)} upstream 5xx passed through, {rec} retried identically and answered 200 (D107)")
ends = sorted(ts(r) + r.get("total_s", 0) for r in relay if r.get("superseded"))
def gin(l):  # "[GIN] 2026/11/05 - 22:01:20 | 500 | ..." -> epoch seconds, local time
    m = re.search(r"\[GIN\] (\d{4}/\d\d/\d\d - \d\d:\d\d:\d\d)", l)
    return dt.datetime.strptime(m.group(1), "%Y/%m/%d - %H:%M:%S").timestamp() if m else None
echo5xx, used = 0, set()
for i in i5xx:
    g = gin(server[i])
    j = next((k for k, e in enumerate(ends) if k not in used and g is not None and abs(g - e) <= 3), None)
    if j is not None: used.add(j); echo5xx += 1
print(f"ollama: {echo5xx} HTTP 5xx within 3 s of a superseded call's end (relay cancel, D112)")
excused5xx = (min(parse5xx, rec) if rec == len(r5xx) else 0) + (echo5xx if aborts <= superseded else 0)
bad += ["client aborts"] * (aborts > superseded) + ["HTTP 5xx"] * (len(i5xx) > excused5xx)
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
    s = dt.datetime.strptime(f"{year}-{r['t']}", "%Y-%m-%d %H:%M:%S").timestamp()
    return any(-1 <= e - s <= 10 and s + r.get("total_s", 0) - e <= 60 for e in ends)
closes = [r for r in relay if r.get("client_closed")]
excused = sum(map(at_agent_end, closes))
print(f"relay: {excused} of {len(closes)} client closes at an agent's end (expected: background review cut, D99)")
c["client_closed"] = len(closes) - excused
bad += [k for k in ("upstream_error", "max_wait_drop", "client_closed") if c[k]]
print("SERVING:", "ok" if not bad else "FAIL: " + "; ".join(bad))
sys.exit(1 if bad else 0)
