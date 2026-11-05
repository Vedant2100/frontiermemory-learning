#!/bin/bash
# Copy the verified gated corpus only to the separate guest; never print its contents.
set -euo pipefail
REPO=$(pwd -P)
[ "$REPO" = "$(realpath "$HOME/frontiermemory-cluster2")" ] || { echo WRONG_WORKTREE; exit 1; }
source official/vm/lib-cluster2.sh
bash official/vm/check-updates-cluster2.sh
vm_boot 4 12G
G 'test ! -e ~/official/frontiermemory/data/corpus/v1.1' || { echo GUEST_CORPUS_ALREADY_EXISTS; exit 1; }
tar -C "$REPO/data/corpus/v1.1" --exclude='./.cache' -cf - . | "${SSH[@]}" 'umask 077; mkdir -p ~/official/frontiermemory/data/corpus/v1.1; tar -xf - -C ~/official/frontiermemory/data/corpus/v1.1'
G 'cd ~/official/frontiermemory/data/corpus/v1.1; test "$(sha256sum SHA256SUMS | cut -d" " -f1)" = 19346a3e46b022ed1def552f8e4f4c50030cefd3250a7a8e10676b46b370b763; sha256sum -c SHA256SUMS >/dev/null 2>&1; echo "GUEST_CORPUS_CHECKSUMS_OK count=$(wc -l < SHA256SUMS)"'
G 'cd ~/official/frontiermemory; .venv/bin/python - <<"PY"
import json
from pathlib import Path
release=json.loads(Path("tasks.json").read_text())["release"]
print("RELEASE_TASK_COUNT",len(release))
print("RELEASE_TASK_IDS", " ".join(sorted(release)))
PY'
