"""Tests for the exploratory arms (results/preregistration-arms.md). Standard library only: run on the host or in the guest.

    python3 -I -m unittest official/tests/test_arms.py      (from the repository root)
Synthetic memories and corpora only; no corpus or memory text is read except the public task list and committed id maps.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
for sub in ("official/fm_local", "official/vm", "scripts"):
    sys.path.insert(0, str(REPO / sub))
import arm_logic  # noqa: E402
import build_placebo  # noqa: E402
import build_recency_corpus as brc  # noqa: E402
import derive_arm  # noqa: E402
import recency_probe  # noqa: E402


def skill(root: Path, rel: str, name: str, desc: str, body: str = "body\n", extra: dict | None = None) -> None:
    d = root / "skills" / rel
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n\n{body}")
    for k, v in (extra or {}).items():
        (d / k).parent.mkdir(parents=True, exist_ok=True)
        (d / k).write_text(v)


def memory(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "MEMORY.md").write_text("# Learned Hermes skills\n\n" + "".join(  # hermes_dream.export_skills's format
        f"- [{s}](skills/{s}/SKILL.md)\n" for s in ("deploy-steps", "deploy-steps/nested", "user-style", "eval-metrics")))
    skill(root, "deploy-steps", "deploy-steps", "Steps to build the docker image and run the release pipeline",
          "Run make release.\n" * 20, {"scripts/run.sh": "echo run\n", "refs/notes.md": "notes ü\n"})
    skill(root, "deploy-steps/nested", "nested-one", "A nested skill about preferences of the user")
    skill(root, "user-style", "user-style", "User preference: changelog formatting and naming conventions",
          "Keep entries short.\n")
    skill(root, "eval-metrics", "eval-metrics", "How to compute word2vec similarity metrics", "Use cosine.\n" * 5)
    (root / "other.md").write_text("loose file\n")
    return root


class LogicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mem = memory(Path(self.tmp.name) / "m")

    def tearDown(self):
        self.tmp.cleanup()

    def test_skills_and_frontmatter(self):
        found = arm_logic.skills(self.mem)
        self.assertEqual([s["rel"] for s in found], ["deploy-steps", "deploy-steps/nested", "eval-metrics", "user-style"])
        self.assertEqual(found[1]["name"], "nested-one")
        self.assertEqual(arm_logic.frontmatter("no frontmatter"), {})
        self.assertEqual(arm_logic.frontmatter("---\nname: x\n"), {})  # unterminated block is not frontmatter

    def test_skill_files_leave_out_nested_skill(self):
        root = self.mem / "skills"
        files = [p.relative_to(root).as_posix() for p in arm_logic.skill_files(root, "deploy-steps",
                                                                                [s["rel"] for s in arm_logic.skills(self.mem)])]
        self.assertEqual(files, ["deploy-steps/SKILL.md", "deploy-steps/refs/notes.md", "deploy-steps/scripts/run.sh"])

    def test_bm25(self):
        found = arm_logic.skills(self.mem)
        top = arm_logic.bm25_select("Train word2vec and report cosine similarity metrics", found, k=2)
        self.assertEqual(top[0]["rel"], "eval-metrics")
        self.assertEqual(len(top), 2)
        self.assertEqual(len(arm_logic.bm25_select("x", found)), arm_logic.K_SCOPED)
        self.assertEqual(len(arm_logic.bm25_select("x", found[:2])), 2)  # fewer skills than k: all
        tie = arm_logic.bm25_select("zzz", found, k=4)  # no term matches: path order
        self.assertEqual([s["rel"] for s in tie], sorted(s["rel"] for s in found))
        self.assertEqual(arm_logic.bm25_scores("a", []), [])

    def test_categorize(self):
        by = {s["rel"]: arm_logic.categorize(s) for s in arm_logic.skills(self.mem)}
        self.assertEqual(by["user-style"], "memory-user-preferences")
        self.assertEqual(by["deploy-steps"], "memory-environment-facts")  # docker
        self.assertEqual(by["eval-metrics"], "memory-procedures")  # no keyword: fallback
        self.assertEqual(set(arm_logic.CATEGORIES), {"memory-user-preferences", "memory-environment-facts", "memory-procedures"})

    def test_cue_match(self):
        terms = {"a": arm_logic.cue_terms("docker release pipeline"), "b": arm_logic.cue_terms("cosine similarity")}
        self.assertEqual(arm_logic.cue_match('terminal {"cmd": "docker build && run release"}', terms, set()), ["a"])
        self.assertEqual(arm_logic.cue_match('terminal {"cmd": "docker ps"}', terms, set()), [])  # one shared term
        self.assertEqual(arm_logic.cue_match("docker release", terms, {"a"}), [])
        self.assertNotIn("file", arm_logic.cue_terms("read the file please"))  # stop word

    def test_build_skills_dir_categories(self):
        out = Path(self.tmp.name) / "out"
        found = arm_logic.skills(self.mem)
        picks = [(s["rel"], f"{arm_logic.categorize(s)}/{s['leaf']}") for s in found]
        arm_logic.build_skills_dir(self.mem, out, picks, {"memory-procedures": "P"})
        self.assertTrue((out / "memory-procedures/eval-metrics/SKILL.md").is_file())
        self.assertFalse((out / "memory-environment-facts/deploy-steps/nested").exists())  # nested skill copied on its own
        self.assertTrue((out / "memory-procedures/DESCRIPTION.md").read_text().startswith("---\ndescription: P"))
        with self.assertRaises(ValueError):
            arm_logic.build_skills_dir(self.mem, out, picks[:1], {})

    def test_available_skills(self):
        self.assertEqual(arm_logic.available_skills("x<available_skills>\n  a:\n</available_skills>y"), "\n  a:\n")
        self.assertEqual(arm_logic.available_skills(None), "")


class CuePluginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.mem, self.log = memory(base / "m"), base / "log"
        self.log.mkdir()
        plugin = base / "fm-cue"
        plugin.mkdir()
        for f in ("__init__.py", "plugin.yaml"):
            (plugin / f).write_bytes((REPO / "official/fm_local/cue_plugin" / f).read_bytes())
        (plugin / "arm_logic.py").write_bytes((REPO / "official/fm_local/arm_logic.py").read_bytes())
        spec = importlib.util.spec_from_file_location("fm_cue_test", plugin / "__init__.py")
        self.p = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.p)
        hooks = {}
        os.environ.update(FM_CUE_MEMORY=str(self.mem), FM_CUE_LOG=str(self.log))
        self.p.register(type("Ctx", (), {"register_hook": lambda _, n, f: hooks.__setitem__(n, f)})())
        self.hook = hooks["transform_tool_result"]

    def tearDown(self):
        self.tmp.cleanup()

    def metrics(self):
        return json.loads((self.log / "fm-cue-metrics.json").read_text())

    def test_fires_once_and_appends(self):
        out = self.hook(tool_name="terminal", args={"command": "docker build . && ./release pipeline"}, result="ok")
        self.assertTrue(out.startswith("ok\n\n[Saved memory skill that matches this step: deploy-steps]"))
        self.assertIn("Run make release.", out)
        self.assertIsNone(self.hook(tool_name="terminal", args={"command": "docker release pipeline"}, result="ok"))
        m = self.metrics()
        self.assertEqual((m["hook_calls"], m["activations"], m["skills"]), (2, 1, 4))
        self.assertEqual(m["inserted_bytes"], len((self.mem / "skills/deploy-steps/SKILL.md").read_bytes()))

    def test_direct_open_is_not_inserted(self):
        self.assertIsNone(self.hook(tool_name="read_file", args={"path": "/tmp/hermes/memories/skills/user-style/SKILL.md"},
                                    result="x"))
        self.assertIsNone(self.hook(tool_name="skill_view", args={"name": "eval-metrics"}, result="x"))
        m = self.metrics()
        self.assertEqual((m["opened_directly"], m["activations"]), (2, 0))

    def test_non_string_result(self):
        out = self.hook(tool_name="terminal", args={"command": "cosine similarity word2vec metrics"}, result={"ok": 1})
        self.assertTrue(out.startswith('{"ok": 1}'))

    def test_register_needs_env(self):
        os.environ.pop("FM_CUE_LOG")
        with self.assertRaises(RuntimeError):
            self.p.register(None)


class PlaceboTests(unittest.TestCase):
    def test_shape_kept_content_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = memory(Path(tmp) / "m")
            out = Path(tmp) / "p"
            report = build_placebo.build(mem, out)
            self.assertTrue(report["ok"], report)
            src = sorted(p.stat().st_size for p in mem.rglob("*") if p.is_file())
            dst = sorted(p.stat().st_size for p in out.rglob("*") if p.is_file())
            self.assertEqual(src, dst)
            self.assertEqual(len(arm_logic.skills(out)), len(arm_logic.skills(mem)))
            text = "".join(p.read_text() for p in out.rglob("*") if p.is_file())
            for leak in ("deploy", "docker", "cosine", "user-style", "Run make release"):
                self.assertNotIn(leak, text)
            self.assertTrue((out / "MEMORY.md").read_text().startswith(build_placebo.INDEX_HEAD + "- [note-01]"))
            self.assertEqual(arm_logic.skills(out)[0]["name"], "note-01")
            with self.assertRaises(ValueError):
                build_placebo.build(mem, out)

    def test_tiny_file_overrun_and_wrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp) / "m"
            mem.mkdir()
            (mem / "MEMORY.md").write_text("x")  # shorter than the index it must hold
            src = Path(tmp) / "s.txt"
            src.write_text("ab")
            report = build_placebo.build(mem, Path(tmp) / "p", src)
            self.assertFalse(report["ok"])
            self.assertGreater(report["header_overrun_bytes"], 0)
            f = build_placebo.Filler("abc")
            self.assertEqual((f.take(7), f.wraps), ("abcabca", 2))

    def test_source_is_ascii_and_large(self):
        text = build_placebo.SOURCE.read_text(encoding="ascii")
        self.assertGreater(len(text), 300_000)
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),
                         "f43086d9f48819cf7e246c473225fe09f2065c1cd3cdc312e6c176da10be7a9c")


def atif(path: Path, start: str, n: int = 3) -> None:
    steps = [{"step_id": i + 1, "source": "user" if i == 0 else "agent", "message": f"m{i}",
              "timestamp": f"{start}T10:0{i}:00Z"} for i in range(n)]
    path.write_text(json.dumps({"schema_version": "ATIF-v1.6", "session_id": "s", "agent": {}, "steps": steps}))


class RecencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.corpus = base / "c"
        (self.corpus / "inputs").mkdir(parents=True)
        days = ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-05", "2026-09-06", "2026-09-07"]
        for i, d in enumerate(days, 1):
            atif(self.corpus / "inputs" / f"t{i:04d}.json", d)
        (self.corpus / "inputs" / "t0008.jsonl").write_text('{"type": "x"}\n')
        (self.corpus / "inputs" / "t0009.json").write_text(json.dumps({"info": {}, "messages": []}))
        self.rel = {"build-word2vec-pipeline": [f"t{i:04d}.json" for i in range(1, 8)] + ["t0008.jsonl", "t0009.json"],
                    "enterpriseops-csm-x": ["t0001.json", "t0002.json"], "cattrs-x": []}

    def tearDown(self):
        self.tmp.cleanup()

    def test_hosts(self):
        hosts = brc.choose_hosts(self.corpus / "inputs", self.rel)
        # word2vec gets 3 pairs (k-th earliest vs k-th latest); enterpriseops' runs are already used
        self.assertEqual(hosts, {"build-word2vec#0": ("t0001.json", "t0007.json"),
                                 "build-word2vec#1": ("t0002.json", "t0006.json"),
                                 "build-word2vec#2": ("t0003.json", "t0005.json")})

    def test_build_a_b_and_probe(self):
        base = Path(self.tmp.name)
        a = brc.build(self.corpus, self.rel, base / "a", "a")
        b = brc.build(self.corpus, self.rel, base / "b", "b")
        self.assertEqual((a["facts_count"], a["files"]), (3, 9))
        self.assertFalse(a["ok"])  # fewer than 6 facts: refused
        fact = a["facts"]["build-word2vec#0"]
        last = json.loads((base / "a/inputs/t0007.json").read_text())["steps"][-1]
        self.assertEqual((last["source"], last["step_id"], last["timestamp"]), ("user", 4, "2026-09-07T10:02:00Z"))
        self.assertIn(fact["current"], last["message"])
        swapped = json.loads((base / "b/inputs/t0001.json").read_text())["steps"]  # b: the later run under the earlier name
        self.assertIn(fact["current"], swapped[-1]["message"])
        self.assertEqual(swapped[0]["timestamp"], "2026-09-07T10:00:00Z")
        self.assertEqual((base / "a/inputs/t0004.json").read_bytes(), (self.corpus / "inputs/t0004.json").read_bytes())
        for line in (base / "a/SHA256SUMS").read_text().splitlines():
            sha, rel = line.split("  ", 1)
            self.assertEqual(hashlib.sha256((base / "a" / rel).read_bytes()).hexdigest(), sha)
        self.assertNotEqual(brc.canary("x#0", "stale"), brc.canary("x#0", "current"))
        mem = base / "mem"
        mem.mkdir()
        (mem / "MEMORY.md").write_text(f"prefix {fact['current']} and {a['facts']['build-word2vec#1']['stale']}")
        res = recency_probe.probe(mem, a["facts"])
        self.assertEqual(res["outcomes"], {"current_only": 1, "stale_only": 1, "neither": 1})
        with self.assertRaises(ValueError):
            brc.build(self.corpus, self.rel, base / "a", "a")

    def test_families_match_recency_check(self):
        sys.path.insert(0, str(REPO / "scripts"))
        src = (REPO / "scripts/recency_check.py").read_text()
        for fam in brc.FAMILIES:
            self.assertIn(f'"{fam}":', src)


class EvidenceMapTests(unittest.TestCase):
    def test_matches_recency_check(self):
        emap = json.loads((REPO / "official/fm_local/evidence-runs.json").read_text())
        rel = json.loads((REPO / "results/recency-check.json").read_text())
        self.assertEqual(set(emap), set(rel))
        self.assertEqual(len(emap), 15)
        for task, names in emap.items():
            self.assertEqual(sorted(Path(n).stem for n in names), sorted(r["id"] for r in rel[task]["runs"]))


class DeriveTests(unittest.TestCase):
    SRC = (REPO / "official/vm/run-set-v1.sbatch").read_text()

    def test_every_arm_derives_and_parses(self):
        for arm, spec in derive_arm.ARMS.items():
            for e2e in (False, True):
                with self.subTest(arm=arm, e2e=e2e):
                    out = derive_arm.derive(arm, self.SRC, e2e)
                    with tempfile.NamedTemporaryFile("w", suffix=".sh") as f:
                        f.write(out)
                        f.flush()
                        self.assertEqual(subprocess.run(["bash", "-n", f.name]).returncode, 0)
                    self.assertIn(f'case "$SET" in arm-{arm})', out)
                    self.assertNotIn("fm_local.hermes_local:LocalHermes $COMMON --tasks", out)
                    self.assertIn("TASKJOB=fm-smoke-$SET" if e2e else "TASKJOB=fm-tasks-$SET", out)
                    if spec["memory"] == "recency":
                        self.assertNotIn('run_tasks "$MEM"\nfor round', out)
                        self.assertIn("recency_probe.py", out)
                    else:
                        self.assertIn(f"--harness {spec['harness']}", out)
                        self.assertIn("\narm_check\nstep \"$SET: score and archive\"", out)
                    if spec["memory"] in ("none", "placebo"):
                        self.assertIn("true || G \"$ENV; frontier-memory bundle", out)
                    if spec["memory"] == "run1":
                        self.assertIn("GENJOB=fm-gen-run1", out)
                        self.assertNotIn("generate-memory", out)
                    if spec["memory"] == "generate":
                        self.assertIn("--harness fm_local.generator_hermes:GeneratorHermesLearn", out)
                    if spec.get("provider") == "anthropic":
                        self.assertIn("-m anthropic/$MODEL", out)

    def test_changed_source_stops(self):
        with self.assertRaises(SystemExit):
            derive_arm.derive("placebo", self.SRC.replace("score and archive", "score"), False)


class ArmCheckTests(unittest.TestCase):
    def run_check(self, arm: str, prompt: str, report: dict | None, extra: dict | None = None,
                  task: str = "build-word2vec-pipeline", memory_meta=None, ephemeral: str = "",
                  config: dict | None = None) -> int:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            mem = memory(cwd / "jobs/fm-gen-run1/gen__1/artifacts/memory")
            assert mem.is_dir()
            trial = cwd / "jobs/task" / f"{task[:32].rstrip('_-')}__abc"  # Harbor's trial name rule
            (trial / "agent").mkdir(parents=True)
            (trial / "result.json").write_text(json.dumps({"task_name": f"letta-ai/{task}",
                                                           "agent_result": {"metadata": {"frontier_memory": memory_meta}}}))
            (trial / "agent/hermes-session.jsonl").write_text(json.dumps({"system_prompt": prompt}) + "\n")
            cfg = config if config is not None else {"agent": {"system_prompt": ephemeral} if ephemeral else {}}
            (trial / "agent/hermes-config.yaml").write_text(yaml.safe_dump(cfg))
            if report is not None:
                (trial / "agent/arm-report.json").write_text(json.dumps(report))
            for k, v in (extra or {}).items():
                (trial / "agent" / k).write_text(json.dumps(v))
            return subprocess.run([sys.executable, "-I", str(REPO / "official/fm_local/arm_check.py"), "jobs/task", arm],
                                  cwd=cwd, capture_output=True).returncode

    def test_readfirst(self):
        # D125: the sentence is Hermes's ephemeral prompt, in the config, never in the saved session prompt
        rf, saved = arm_logic.READ_FIRST, "# Learned Hermes skills"
        rep = {"arm": "readfirst", "system_prompt_sha256": hashlib.sha256(rf.encode()).hexdigest()}
        self.assertEqual(self.run_check("readfirst", saved, rep, ephemeral=rf), 0)
        self.assertEqual(self.run_check("readfirst", saved, rep), 1)  # the failure seen on Nov 7: not in the config either
        self.assertEqual(self.run_check("readfirst", saved, {"arm": "readfirst"}, ephemeral=rf), 1)  # report lacks the digest
        self.assertEqual(self.run_check("readfirst", saved, rep, ephemeral=rf + " Extra."), 1)  # not exactly the sentence
        self.assertEqual(self.run_check("readfirst", "no memory block", rep, ephemeral=rf), 1)
        self.assertEqual(self.run_check("readfirst", saved, None, ephemeral=rf), 1)
        self.assertEqual(self.run_check("readfirst", saved, rep,  # a personality would replace agent.system_prompt
                                        config={"agent": {"system_prompt": rf}, "display": {"personality": "pirate"}}), 1)

    def test_scoped_counts_only_the_index(self):
        idx = "<available_skills>\n  general:\n    - deploy-steps: d\n    - eval-metrics: e\n    - user-style: u\n</available_skills>"
        rep = {"arm": "scoped", "selected": 3}
        self.assertEqual(self.run_check("scoped", "MEMORY nested-one\n" + idx, rep), 0)
        self.assertEqual(self.run_check("scoped", idx.replace("    - user-style: u\n", ""), rep), 1)

    def test_cue(self):
        ok = {"fm-cue-metrics.json": {"hook_calls": 3, "skills": 4}}
        self.assertEqual(self.run_check("cue", "<available_skills>\n</available_skills>", {"arm": "cue"}, ok), 0)
        self.assertEqual(self.run_check("cue", "<available_skills>\n</available_skills>", {"arm": "cue"}), 1)
        self.assertEqual(self.run_check("cue", "# Learned Hermes skills", {"arm": "cue"}, ok), 1)

    def test_evidence(self):
        emap = json.loads((REPO / "official/fm_local/evidence-runs.json").read_text())
        for task in ("build-word2vec-pipeline", "automationbench-marketing-content-gap-analysis"):  # 2nd: name > 32 chars
            n = len(emap[task])
            sp = arm_logic.POINTER["evidence"].format(n=n, path=arm_logic.RECORDS_TARGET)
            self.assertEqual(self.run_check("evidence", sp, {"arm": "evidence", "records": n}, task=task), 0)
            self.assertEqual(self.run_check("evidence", sp, {"arm": "evidence", "records": n - 1}, task=task), 1)
        sp = "no pointer"
        self.assertEqual(self.run_check("evidence", sp, {"arm": "evidence", "records": 0},
                                        task="customer-delivery-contextual-preferences"), 0)

    def test_api_harness_memory_metadata(self):  # as frontier_memory.agents.memory_metadata writes it
        with_mem = {"sha256": "ab" * 32, "total_bytes": 1, "files": []}
        self.assertEqual(self.run_check("cm", "", None, memory_meta=with_mem), 0)
        self.assertEqual(self.run_check("cm", "", None, memory_meta=None), 1)
        self.assertEqual(self.run_check("c0", "", None, memory_meta=None), 0)
        self.assertEqual(self.run_check("k0", "", None, memory_meta=with_mem), 1)

    def test_nested_skill_ranked_before_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = memory(Path(tmp) / "m")
            arm_logic.build_skills_dir(mem, Path(tmp) / "o", [("deploy-steps/nested", "deploy-steps/nested"),
                                                              ("deploy-steps", "deploy-steps")], {})
            self.assertTrue((Path(tmp) / "o/deploy-steps/nested/SKILL.md").is_file())
            self.assertTrue((Path(tmp) / "o/deploy-steps/SKILL.md").is_file())

    def test_finished_invalid_generation_not_redone(self):
        out = derive_arm.derive("generator", DeriveTests.SRC, True)
        self.assertIn("generation finished without valid memory; not redone (prereg)", out)
        self.assertLess(out.index("ls jobs/$GENJOB/*__*/result.json"), out.index("fresh generation"))


class EffortProbeTests(unittest.TestCase):
    """effort_probe.py against a local fake server: reasoning grows with effort; Codex's "max" can be refused."""

    def serve(self, refuse_max: bool):
        import http.server
        import threading

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                effort = (body.get("reasoning") or {}).get("effort")
                if refuse_max and effort == "max":
                    self.send_response(400)
                    self.end_headers()
                    return
                n = {"low": 10, "xhigh": 400, "max": 900}.get(effort, 0)
                if self.path == "/v1/responses":
                    doc = {"usage": {"output_tokens_details": {"reasoning_tokens": n}}, "output": []}
                else:
                    doc = {"content": [{"type": "thinking", "thinking": "x" * (4000 if "thinking" in body else 0)}]}
                data = json.dumps(doc).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        return srv.server_address[1]

    def test_probe(self):
        import effort_probe
        lines, rejected = effort_probe.summarize(effort_probe.run(self.serve(False), "m"))
        self.assertFalse(rejected)
        text = "\n".join(lines)
        self.assertIn("setting=max used_by='Codex' status=[200] reasoning_mean=900", text)
        self.assertIn("setting=thinking-16k", text)
        lines, rejected = effort_probe.summarize(effort_probe.run(self.serve(True), "m"))
        self.assertTrue(rejected)

    def test_driver_checks_stage(self):
        src = (REPO / "official/vm/next-study-3.sh").read_text()
        self.assertIn('[ "${STAGE:-all}" = checks ] && continue  # checks only: no counted set', src)
        self.assertLess(src.index("effort-check.sh"), src.index("for arm in $ORDER"))


if __name__ == "__main__":
    unittest.main()
