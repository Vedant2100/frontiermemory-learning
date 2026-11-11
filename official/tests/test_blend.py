"""Tests for the blend arm (results/preregistration-arms.md, B6): the rewrite contract, the rewrite script against a fake model
server (re-roll, resume, too few valid tasks), and the per-trial check. Standard library only.

    python3 -m unittest official/tests/test_blend.py     (from the repository root)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "official/fm_local"))
import blend_check  # noqa: E402
import blend_logic as B  # noqa: E402

ORIG = ("Train a word2vec model on `/app/corpus.txt` and write `/app/report.md`. Use the function `eval_metrics` and the flag "
        "--window 5. Finish within 20 min. Report 3 cosine similarities.")


class Contract(unittest.TestCase):
    def test_items(self):
        items = B.required_items(ORIG)
        for want in ("/app/corpus.txt", "/app/report.md", "eval_metrics", "--window", "20 min", "3"):
            self.assertIn(want, items)

    def test_faithful_rewrite_passes(self):
        new = ORIG + " Cosine scores between related words are usually above 0.5, so check the vocabulary size first."
        self.assertEqual(B.contract_check(ORIG, new), [])

    def test_missing_item_fails(self):
        bad = ORIG.replace("--window 5", "a window of five") + " Extra context sentence here."
        self.assertTrue(any("missing" in p for p in B.contract_check(ORIG, bad)))

    def test_talk_of_notes_fails_unless_original_has_it(self):
        self.assertTrue(any("mentions" in p for p in B.contract_check(ORIG, ORIG + " Earlier runs showed this works.")))
        orig2 = ORIG + " Keep memory use low."
        self.assertEqual(B.contract_check(orig2, orig2 + " Check vocabulary size."), [])

    def test_shorter_preface_and_empty_fail(self):
        self.assertTrue(any("shorter" in p for p in B.contract_check(ORIG, ORIG[:40])))
        self.assertTrue(any("preface" in p for p in B.contract_check(ORIG, "Here is the rewritten task: " + ORIG)))
        self.assertEqual(B.contract_check(ORIG, "  "), ["empty rewrite"])

    def test_unchanged_original_is_valid_and_adds_nothing(self):
        self.assertEqual(B.contract_check(ORIG, ORIG), [])
        self.assertEqual(B.added_sentences(ORIG, ORIG), 0)

    def test_thinking_is_stripped(self):
        self.assertEqual(B.strip_thinking("<think>plan\nmore</think>\nAnswer."), "Answer.")

    def test_numbered_list_markers_are_not_required_numbers(self):
        orig = "Do these:\n1. Read `a.txt`.\n2. Write `b.txt`."
        self.assertNotIn("2", [i for i in B.required_items(orig) if i == "2"])
        self.assertEqual(B.contract_check(orig, "Do these steps in order:\n- Read `a.txt`.\n- Write `b.txt`. Be careful."), [])


class FakeModel(BaseHTTPRequestHandler):
    """Answers /chat/completions: seed 1 breaks the contract for the task named in BAD, seed 2 and every other call keep it."""
    calls: list = []
    BAD: set = set()

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        prompt = body["messages"][0]["content"]
        original = prompt.split("=== ORIGINAL TASK DESCRIPTION ===\n", 1)[1]
        FakeModel.calls.append(body["seed"])
        text = original + " Background: check the vocabulary size first."
        if any(b in original for b in FakeModel.BAD) and body["seed"] == 1:
            text = "Do the task."
        if any(b in original for b in FakeModel.BAD) and body["seed"] == 2 and "ALWAYS" in original:
            text = "Do the task."
        out = json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": text}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


class Rewrite(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        (self.t / "mem").mkdir()
        (self.t / "mem/MEMORY.md").write_text("# Notes\n- a fact about `eval_metrics`\n")
        self.tasks = self.t / "tasks"
        for i in range(12):
            d = self.tasks / f"task-{i:02d}"
            d.mkdir(parents=True)
            (d / "instruction.md").write_text(f"Task {i}: read `/app/in{i}.csv`, write `/app/out{i}.txt`, within {20 + i} min.")
        self.server = HTTPServer(("127.0.0.1", 0), FakeModel)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        FakeModel.calls, FakeModel.BAD = [], set()
        self.env = {**os.environ, "FM_LOCAL_BASE_URL": f"http://127.0.0.1:{self.server.server_port}/v1"}

    def tearDown(self):
        self.server.shutdown()
        self.tmp.cleanup()

    def run_rewrite(self):
        return subprocess.run([sys.executable, str(REPO / "official/fm_local/blend_rewrite.py"), str(self.t / "mem"), str(self.tasks),
                               str(self.t / "map.json"), str(self.t / "report.json")], capture_output=True, text=True, env=self.env)

    def test_reroll_resume_and_report(self):
        FakeModel.BAD = {"Task 3:"}
        r = self.run_rewrite()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        m = json.loads((self.t / "map.json").read_text())
        self.assertTrue(m["task-03"]["ok"] and m["task-03"]["rolls"] == 2 and m["task-00"]["rolls"] == 1)
        self.assertEqual(len(FakeModel.calls), 13)
        n = len(FakeModel.calls)
        self.assertEqual(self.run_rewrite().returncode, 0)  # resume: nothing is drawn again
        self.assertEqual(len(FakeModel.calls), n)
        rep = json.loads((self.t / "report.json").read_text())
        self.assertEqual((rep["tasks"], rep["valid"], rep["failed"]), (12, 12, []))
        self.assertNotIn("blend", json.dumps(rep["per_task"]["task-00"]).replace("blend_sha", "").replace("blend_chars", ""))
        self.assertNotIn("vocabulary", (self.t / "report.json").read_text())  # no text in the report

    def test_failing_twice_keeps_the_original_and_too_few_stops(self):
        for i in range(12):
            (self.tasks / f"task-{i:02d}/instruction.md").write_text(f"ALWAYS Task {i}: read `/app/in{i}.csv`.")
        FakeModel.BAD = {"ALWAYS"}
        r = self.run_rewrite()
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("TOO_FEW_VALID", r.stdout)
        m = json.loads((self.t / "map.json").read_text())
        self.assertFalse(m["task-00"]["ok"])
        self.assertIsNone(m["task-00"]["blend"])

    def test_model_unreachable_is_not_a_contract_failure(self):
        self.server.shutdown()
        self.server.server_close()  # a closed port refuses at once; an open but silent one would wait for the call timeout
        r = self.run_rewrite()
        self.assertEqual(r.returncode, 1)
        self.assertIn("BLEND_MODEL_ERROR", r.stdout)


class Check(unittest.TestCase):
    def trial(self, root, name, task, report, first_user):
        t = root / name
        (t / "agent").mkdir(parents=True)
        (t / "result.json").write_text(json.dumps({"task_name": f"letta-ai/{task}"}))
        if report is not None:
            (t / "agent/arm-report.json").write_text(json.dumps(report))
        (t / "agent/hermes-session.jsonl").write_text(json.dumps({"messages": [{"role": "user", "content": first_user}]}) + "\n")

    def test_trial_checks(self):
        blend = ORIG + " Check the vocabulary size first."
        bmap = {"t1": {"ok": True, "blend": blend, "blend_sha": B.sha(blend), "orig_sha": B.sha(ORIG)},
                "t2": {"ok": False, "blend": None, "orig_sha": B.sha(ORIG)}}
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.trial(d, "a__1", "t1", {"arm": "blend", "blend_sha256": B.sha(blend)}, blend)
            self.trial(d, "b__2", "t2", {"arm": "blend", "blend_sha256": B.sha(ORIG)}, ORIG)  # fell back to the original
            self.trial(d, "c__3", "t1", {"arm": "blend", "blend_sha256": B.sha(blend)}, ORIG)  # the model got the wrong text
            self.trial(d, "d__4", "t1", None, blend)
            self.assertEqual(blend_check.check_trial(d / "a__1", bmap), [])
            self.assertEqual(blend_check.check_trial(d / "b__2", bmap), [])
            self.assertTrue(blend_check.check_trial(d / "c__3", bmap))
            self.assertEqual(blend_check.check_trial(d / "d__4", bmap), ["no arm report"])


class Derive(unittest.TestCase):
    def test_both_modes_derive_and_parse(self):
        for e2e in ("", "E2E=1"):
            out = Path(tempfile.mkdtemp()) / "s.sh"
            env = {**os.environ, "DRY_RUN": "1", "DRY_OUT": str(out), "REPO": str(REPO)}
            if e2e:
                env["E2E"] = "1"
            r = subprocess.run(["bash", str(REPO / "official/vm/run-blend.sh")], capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            text = out.read_text()
            self.assertIn("blend_hermes:BlendHermes", text)
            self.assertIn("blend_check.py", text)
            self.assertIn("NO_VALID_MEMORY: too few valid rewrites", text)


if __name__ == "__main__":
    unittest.main()
