#!/usr/bin/env bash
# Submit the A6 (Word2Vec) and A7 (DAPT) mechanism-probe jobs, chained after the confirmatory matrix.
# Memories are built by scripts/derive_mechanism_memories.py (digests in results/mechanism-memories.json).
# Both configurations pass `run_codex_ollama_trial.sh --dry-run-arms` (2026-11-01).
# Usage: bash scripts/submit_mechanism_jobs.sh <last-matrix-job-id>
set -euo pipefail
AFTER="${1:?usage: submit_mechanism_jobs.sh <last-matrix-job-id>}"
cd "$(dirname "$0")/.."
M="${PWD}/memory"
M3="M3=${M}/frozen-v5-fullindex@4a2eb5286366d650260af0b873a91be9f99b2891a327f0ae73ba8c2e8ef0517a"

A6=$(TASK=build-word2vec-pipeline \
  MEMORY_ARMS="${M3};M3S=${M}/frozen-m3-s@69bc7113e701881be5a058d4b2c6c022b3cadd1a526ab3f4e4df6b185b6a5509;M3W=${M}/frozen-m3-w@2f1e2e8f0c3992b704d7a57c44d7162932e37e9e8df7e1d90bb0b0271898b4c4" \
  TRIAL_ORDER="M3 M3S M3W M3S M3W M3 M3W M3 M3S M3 M3S M3W M3S M3W M3" \
  sbatch --parsable --export=ALL --time=12:00:00 --job-name=fm-serial \
    --dependency="afterany:${AFTER},singleton" slurm/run-codex-ollama-trial.sbatch)
echo "A6 job ${A6}"

# A7 cutoff (prereg A7): stopped at 2026-11-07 23:59; --time-min lets Slurm shorten the limit to fit.
A7=$(TASK=dapt-intrusion-detection-workflow-learning \
  MEMORY_ARMS="${M3};M3D=${M}/frozen-m3-d@57b0207596ff1c40a3452b6b1f6d001977d4695e212c47718f2ba0c998559c5f" \
  TRIAL_ORDER="M3 M3D M3D M3 M3D M3 M3 M3D M3 M3D" \
  sbatch --parsable --export=ALL --time=24:00:00 --time-min=01:00:00 --deadline=2026-11-07T23:59:00 \
    --job-name=fm-serial --dependency="afterany:${A6},singleton" slurm/run-codex-ollama-trial.sbatch)
echo "A7 job ${A7}"
