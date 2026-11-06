"""Derive one exploratory arm's set script from run-set-v1.sbatch (results/preregistration-arms.md).

Exact string replacements only, each of which must match once, so resume, no-reward reruns, judge, key audit, summary and
audit stay identical to the counted sets; if run-set-v1.sbatch changes, derivation stops instead of guessing.

    python3 official/vm/derive_arm.py <arm> <run-set-v1.sbatch> <out> [--e2e]
    python3 official/vm/derive_arm.py --list
--e2e: one Word2Vec attempt into fm-smoke-arm-<arm>, never counted. The arm check (fm_local/arm_check.py) runs on every
trial in both modes; a failure prints ARM_CHECK_FAILED and stops the set before scoring.
"""

from __future__ import annotations

import sys

HERMES = "fm_local.hermes_local:LocalHermes"
ARM = "fm_local.arm_hermes:ArmHermes --ak arm={}"
CORPUS = "--ak corpus_dir=\\$PWD/data/corpus/v1.1/inputs"
# memory: run1 = HM run 1's generation, reused; none; placebo = built from run 1; generate = a fresh generation of this arm;
# recency = generation only, on a perturbed corpus copy, then a probe (no task trials).
ARMS = {
    "placebo":      {"harness": HERMES, "memory": "placebo"},
    "readfirst":    {"harness": ARM.format("readfirst"), "memory": "run1"},
    "scoped":       {"harness": ARM.format("scoped"), "memory": "run1"},
    "cue":          {"harness": ARM.format("cue"), "memory": "run1"},
    "raw":          {"harness": f"{ARM.format('raw')} {CORPUS}", "memory": "none"},
    "evidence":     {"harness": f"{ARM.format('evidence')} {CORPUS} --ak evidence_map=\\$HOME/official/fm_local/evidence-runs.json",
                     "memory": "none"},
    "categorized":  {"harness": ARM.format("categorized"), "memory": "run1"},
    "generator":    {"harness": HERMES, "memory": "generate", "gen_harness": "fm_local.generator_hermes:GeneratorHermesLearn"},
    "c0":           {"harness": "fm_local.codex_local:LocalCodex", "memory": "none", "api": "/v1/responses"},
    "cm":           {"harness": "fm_local.codex_local:LocalCodex", "memory": "run1", "api": "/v1/responses"},
    "k0":           {"harness": "fm_local.claude_code_local:LocalClaudeCode", "memory": "none", "api": "/v1/messages",
                     "provider": "anthropic"},
    "km":           {"harness": "fm_local.claude_code_local:LocalClaudeCode", "memory": "run1", "api": "/v1/messages",
                     "provider": "anthropic"},
    "recency-a":    {"harness": HERMES, "memory": "recency", "variant": "a"},
    "recency-b":    {"harness": HERMES, "memory": "recency", "variant": "b"},
}

MEM_START = 'MEM=""\nif [ "$SET" != control ] || [ "$SMOKE" = 1 ]; then\n'
MEM_END = '\nrun_tasks "$MEM"\nfor round in 1 2 3;'
GEN_LINE = ('frontier-memory generate-memory --corpus data/corpus/v1.1 --harness fm_local.hermes_local:LocalHermesLearn '
            '$COMMON --ak reasoning_effort=max --job-name $GENJOB --jobs-dir jobs')
CHECK_MEMORY = ('G "$ENV; frontier-memory check-memory jobs/$GENJOB 2>&1 | tail -8 | cut -c1-120; '
                'frontier-memory check-memory jobs/$GENJOB >/dev/null 2>&1"')


def generation(corpus: str, harness: str) -> str:
    gen = GEN_LINE.replace("data/corpus/v1.1", corpus).replace("fm_local.hermes_local:LocalHermesLearn", harness)
    return ('if ! G "$ENV; frontier-memory check-memory jobs/$GENJOB >/dev/null 2>&1"; then\n'
            '  step "$SET: fresh generation"\n'
            f'  G "$ENV; [ ! -e jobs/$GENJOB ] || sudo mv jobs/$GENJOB jobs/$GENJOB.failed-\\$(date +%s); $H {gen} 2>&1 | '
            'tail -1 | cut -c1-140; sudo chown -R fm:fm jobs/$GENJOB"\n'
            'fi\n'
            f'{CHECK_MEMORY} || {{ step "$SET: NO_VALID_MEMORY: reported, trials not run (prereg)"; exit 0; }}\n')


def memory_block(arm: str, spec: dict) -> str:
    kind = spec["memory"]
    if kind == "none":
        return 'MEM=""\n'
    if kind == "run1":
        return ('GENJOB=fm-gen-run1  # HM run 1\'s memory, reused; never generated here\n'
                f'{CHECK_MEMORY} || {{ step "$SET: NO_RUN1_MEMORY_FAILED"; exit 1; }}\n'
                'MEM="--memory jobs/$GENJOB"\n')
    if kind == "placebo":
        return ('GENJOB=fm-mem-placebo  # built once from fm-gen-run1 (fm_local/build_placebo.py), then reused\n'
                'G "$ENV; [ -d jobs/$GENJOB ] || python3 ~/official/fm_local/build_placebo.py jobs/fm-gen-run1 jobs/$GENJOB; '
                'grep -q \'\\"ok\\": true\' jobs/$GENJOB.placebo-report.json" || { step "$SET: PLACEBO_BUILD_FAILED"; exit 1; }\n'
                f'{CHECK_MEMORY} || {{ step "$SET: PLACEBO_BUILD_FAILED"; exit 1; }}\n'
                'MEM="--memory jobs/$GENJOB"\n')
    if kind == "generate":
        return f'GENJOB=fm-gen-arm-{arm}\n' + generation("data/corpus/v1.1", spec["gen_harness"]) + 'MEM="--memory jobs/$GENJOB"\n'
    if kind == "recency":
        v = spec["variant"]
        return (f'GENJOB=fm-gen-arm-recency-{v}; RCORPUS=data/corpus/recency-{v}\n'
                f'G "$ENV; [ -d $RCORPUS ] || python3 ~/official/fm_local/build_recency_corpus.py data/corpus/v1.1 '
                f'~/official/fm_local/evidence-runs.json $RCORPUS {v}; grep -q \'\\"ok\\": true\' $RCORPUS.facts.json" '
                '|| { step "$SET: RECENCY_CORPUS_FAILED"; exit 1; }\n'
                + generation("$RCORPUS", "fm_local.hermes_local:LocalHermesLearn") + 'MEM="--memory jobs/$GENJOB"\n')
    raise ValueError(kind)


def derive(arm: str, src: str, e2e: bool) -> str:
    spec = ARMS[arm]
    model = f"-m {spec.get('provider', 'openai')}/$MODEL -e docker --allow-host 10.0.2.2"
    pairs = [
        ('case "$SET" in control|run1|run2|run3) ;; *) echo "bad SET"; exit 2 ;; esac',
         f'case "$SET" in arm-{arm}) ;; *) echo "bad SET"; exit 2 ;; esac'),
        ('else ATTEMPTS=3; FILTER=""; TASKJOB=fm-tasks-$SET; GENJOB=fm-gen-$SET; fi',
         "else ATTEMPTS=1; FILTER=\"-i 'build-word2vec*'\"; TASKJOB=fm-smoke-$SET; GENJOB=none; fi" if e2e else
         'else ATTEMPTS=3; FILTER=""; TASKJOB=fm-tasks-$SET; GENJOB=none; fi'),
        ('--harness fm_local.hermes_local:LocalHermes $COMMON --tasks', f'--harness {spec["harness"]} {model} --tasks'),
        ('MODEL=qwen3.8:27b-mtp-q4_K_M; JUDGE=', ARM_CHECK.format(arm=arm, api=spec.get("api", "")) + 'MODEL=qwen3.8:27b-mtp-q4_K_M; JUDGE='),
        ('\nstep "$SET: score and archive"', '\narm_check\nstep "$SET: score and archive"'),
        ('G "nohup bash ~/official/fm_local/key_audit.sh',
         'R0=$(wc -l < "$OLOG/relay.log" 2>/dev/null || echo 0)\nG "nohup bash ~/official/fm_local/key_audit.sh'),
    ]
    if spec["memory"] not in ("run1", "generate", "recency"):  # no generation job to bundle
        pairs.append(('[ "$SET" = control ] && [ "$SMOKE" != 1 ] || G "$ENV; frontier-memory bundle',
                      'true || G "$ENV; frontier-memory bundle'))
    for a, b in pairs:
        if src.count(a) != 1:
            raise SystemExit(f"run-set-v1.sbatch changed: expected one match, found {src.count(a)}: {a[:70]!r}")
        src = src.replace(a, b)
    i, j = src.find(MEM_START), src.find(MEM_END)
    if src.count(MEM_START) != 1 or src.count(MEM_END) != 1 or not 0 < i < j:
        raise SystemExit("run-set-v1.sbatch changed: memory block not found once")
    src = src[:i] + memory_block(arm, spec) + src[j:]
    if spec["memory"] == "recency":  # generation and probe only: cut from the task run to the cleanup line
        k, stop = src.find(MEM_END), src.find("\nvm_stop; trap - EXIT;")
        if not 0 < k < stop or src.count("\nvm_stop; trap - EXIT;") != 1:
            raise SystemExit("run-set-v1.sbatch changed: task section not found once")
        probe = ('\nstep "$SET: recency probe of the generated memory (no task trials)"\n'
                 'G "$ENV; python3 ~/official/fm_local/recency_probe.py jobs/$GENJOB $RCORPUS.facts.json" '
                 '| tee "$REPO/results/official/recency-probe-$SET.txt"\n'
                 '"${SCP[@]}" "fm@127.0.0.1:official/frontiermemory/$RCORPUS.facts.json" "$REPO/results/official/recency-facts-$SET.json"')
        src = src[:k] + probe + src[stop:]
    return src


ARM_CHECK = '''arm_check() {{  # every trial carries the arm (fm_local/arm_check.py); API arms: the relay saw the harness's own API path
  G "cd ~/official/frontiermemory; sudo python3 ~/official/fm_local/arm_check.py jobs/$TASKJOB {arm}" || {{ echo "ARM_CHECK_FAILED"; exit 1; }}
  if [ -n "{api}" ]; then
    local n; n=$(tail -n +"$(( R0 + 1 ))" "$OLOG/relay.log" | grep -c '"path": "{api}"' || true)
    echo "ARM_API_CHECK path={api} requests=$n"; [ "$n" -gt 0 ] || {{ echo "ARM_CHECK_FAILED"; exit 1; }}
  fi
}}
'''


def main(argv: list[str]) -> int:
    if argv[1:] == ["--list"]:
        print(" ".join(ARMS))
        return 0
    arm, src, out = argv[1], argv[2], argv[3]
    if arm not in ARMS:
        raise SystemExit(f"unknown arm {arm!r}; one of: {' '.join(ARMS)}")
    open(out, "w").write(derive(arm, open(src).read(), "--e2e" in argv))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
