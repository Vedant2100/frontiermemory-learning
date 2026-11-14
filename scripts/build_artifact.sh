#!/bin/bash
# Build the anonymized review artifact for FORGE. Copies code, protocol, preregistration, audit notes and per-trial summaries,
# scrubs identifying strings, then fails if any remain. Gated corpus, memories, trial folders and logs are never included.
# Usage: scripts/build_artifact.sh OUT_DIR   (writes OUT_DIR/frontiermemory-audit-artifact.tar.gz; uploads nothing)
set -euo pipefail
OUT=${1:?output directory}; REPO=$(cd "$(dirname "$0")/.." && pwd)
STAGE=$(mktemp -d); A=$STAGE/artifact; mkdir -p "$A"
cd "$REPO"
INCLUDE=(official/fm_local official/vm/lib.sh official/vm/build-and-test-vm.sbatch official/vm/provision.sbatch official/vm/oracle-all.sbatch
         official/vm/freeze-disk.sbatch official/vm/run-set.sbatch official/vm/run-all.sbatch official/vm/regen-summary.sh official/set-openai-key.sh
         scripts/analyze_official.py scripts/analyze_matrix.py scripts/results_table.py scripts/corpus_coverage.py scripts/harness_exposure.py
         results/protocol-v4-official.md results/preregistration-v2.md results/pipeline-audit.md results/harness-exposure-survey.md
         results/corpus-coverage.json results/official
         official/vm/check-serving.py official/vm/audit-set.py official/vm/run-exposure.sh official/vm/next-study-3.sh official/vm/next-study-4.sh
         official/tests scripts/partial_credit.py scripts/leaderboard_noise.py scripts/memory_access.py scripts/analyze_arms.py
         results/preregistration-arms.md results/decisions-log-detailed.md
         FINAL-RESULTS.md results/paper-supplement-rq2-factors.md official/vm/next-study-5.sh official/vm/next-study-6.sh official/vm/handover-b5.sh
         official/vm/handover-b6.sh official/vm/derive_arm.py official/vm/derive_blend.py official/vm/run-blend.sh official/vm/extract-blend.sbatch
         official/vm/serving-incidents-d136.json)
for p in "${INCLUDE[@]}"; do [ -e "$p" ] && { mkdir -p "$A/$(dirname "$p")"; cp -r "$p" "$A/$p"; }; done
mkdir -p "$A/results"; git for-each-ref --sort=creatordate --format='%(creatordate:iso8601)  %(refname:short)' 'refs/tags/prereg*' > "$A/results/prereg-timestamps.txt"
find "$A" -name '__pycache__' -prune -exec rm -r {} + ; find "$A" -name '*.log' -delete
# Scrub identifiers. Order matters: longest first.
find "$A" -type f \( -name '*.py' -o -name '*.sh' -o -name '*.sbatch' -o -name '*.md' -o -name '*.json' -o -name '*.jsonl' -o -name '*.yaml' -o -name '*.txt' \) -print0 | xargs -0 sed -i -E \
  -e 's#/home/csgrad/vbork001/shared-mem-gov-pilot/models#/path/to/ollama-models#g' \
  -e 's#/home/csgrad/vbork001/frontiermemory-experiment-20261024#/path/to/repo#g' \
  -e 's#/home/csgrad/vbork001#/path/to/home#g' -e 's#/scratch/\$USER#/path/to/local-disk#g' \
  -e 's/nodevcggpu0[1-3]/gpu-node/g' -e 's/--partition=vcggpu/--partition=gpu/g' -e 's/\bvcggpu\b/gpu-partition/g' \
  -e 's/vbork001|csgrad|Vedant[A-Za-z0-9-]*|compfly/anon/g' -e 's/bender-sonnet-agent/second-machine-agent/g' -e 's/[Bb]ender/second-machine/g' -e 's/crisnas1|cris\.local/cluster/g'
cat > "$A/README.md" <<'R'
# Review artifact: FrontierMemory audit

Code and records for the paper's official-setup study. The gated FrontierMemory corpus, the generated memories and the raw
trial folders aren't included: the corpus license doesn't allow redistribution. Paths and host names are replaced by placeholders.

- `results/protocol-v4-official.md`: the setup, item by item, with every difference from official runs.
- `results/preregistration-v2.md`: the written plan and its dated amendments. It was tagged in version control before any counted trial; `results/prereg-timestamps.txt` lists every tag with its commit time. It was not filed with a public registry.
- `results/official/summary-*.jsonl`: one line per trial (task, reward, validity, memory digest, tokens, times).
- `scripts/analyze_official.py`: the preregistered analysis (`--test` runs its self-test).
- `official/`: how the official pipeline was run: a Docker VM, the local-model adapter, the run jobs.
R
LEAK='bender|vbork001|csgrad|nodevcggpu|Vedant|compfly|crisnas|cris\.local|amitroy|ygarg|mukunz|sk-ant-|sk-svcacct|sk-proj-'
if grep -rniE "$LEAK" "$A"; then echo "ARTIFACT_LEAK: identifiers remain; nothing written"; rm -r "$STAGE"; exit 1; fi
for k in "$HOME"/.config/frontiermemory/*-api-key; do [ -f "$k" ] && grep -rqF "$(tr -d '\n' < "$k")" "$A" && { echo "ARTIFACT_LEAK: a key"; rm -r "$STAGE"; exit 1; }; done
mkdir -p "$OUT"; tar -czf "$OUT/frontiermemory-audit-artifact.tar.gz" -C "$STAGE" artifact
echo "files: $(find "$A" -type f | wc -l)  size: $(du -sh "$OUT/frontiermemory-audit-artifact.tar.gz" | cut -f1)"; rm -r "$STAGE"
echo "ARTIFACT_OK $OUT/frontiermemory-audit-artifact.tar.gz"
