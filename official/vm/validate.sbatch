#!/bin/bash
# Protocol v4 validation inside the Docker guest: official tools, corpus v1.1, tasks, network probe, oracle. CPU only, no model.
#SBATCH --job-name=fm-validate
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu01
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=official/logs/validate-%j.log
set -uo pipefail
REPO=$PWD; source official/vm/lib.sh
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $*"; }
vm_boot 14 56G || exit 1
G() { "${SSH[@]}" "$@"; }
ENV='cd ~/official/frontiermemory && . .venv/bin/activate'

step "install official tools at upstream 9af28c2"
G 'set -e; sudo apt-get -qq update; sudo apt-get -qq -y install python3-venv git >/dev/null; mkdir -p ~/official; cd ~/official
[ -d frontiermemory ] || git clone -q https://github.com/letta-ai/frontiermemory; cd frontiermemory; git checkout -q 9af28c2f8210779f442aa36a1d73553630441af5; git log --oneline -1
[ -x ~/boot/bin/uv ] || { python3 -m venv ~/boot; ~/boot/bin/pip -q install uv==0.11.21; }
[ -d .venv ] || ~/boot/bin/uv -q venv --python 3.12; . .venv/bin/activate; ~/boot/bin/uv -q pip install -e .; python --version; harbor --version; frontier-memory --help | head -1' || { echo INSTALL_FAILED; exit 1; }

step "corpus v1.1 (stays on this cluster)"
G 'mkdir -p ~/official/frontiermemory/data/corpus'; "${SCP[@]}" "$REPO/data/corpus/v1.1" "fm@127.0.0.1:official/frontiermemory/data/corpus/"
G "$ENV; python -c \"from pathlib import Path; from frontier_memory.corpus import verify_corpus; print('digest', verify_corpus(Path('data/corpus/v1.1')))\""

step "official tasks from Harbor Hub, checked against tasks.json release"
G "$ENV; [ -d data/tasks ] || harbor dataset download letta-ai/frontier-memory@v1.0 -o data/tasks 2>&1 | tail -3; find data/tasks -name task.toml | wc -l"
G "$ENV"'; python - <<PY
import json
from pathlib import Path
try:
    from dirhash import dirhash
except ImportError:
    print("dirhash not available; checksums not compared"); raise SystemExit
want=json.load(open("tasks.json"))["release"]
for toml in sorted(Path("data/tasks").rglob("task.toml")):
    n=toml.parent.name; h=dirhash(toml.parent,"sha256"); w=want.get(n)
    print(n, "OK" if (w==h or (isinstance(w,str) and h in w)) else "MISMATCH")
PY'

step "network probe on the memory-generation task"
G "$ENV; frontier-memory build-memory-task --corpus data/corpus/v1.1 --out build/memory-task 2>&1 | tail -1; harbor run -p build/memory-task -a frontier_memory.agents.probe:NetworkProbe -e docker --allow-agent-host api.anthropic.com --jobs-dir jobs --job-name probe -y 2>&1 | tail -4; find jobs/probe -name network-probe.json -exec cat {} \;"

step "oracle on all 15 tasks"
"${SSH[@]}" 'umask 077; cat > ~/.openai-key' < "$HOME/.config/frontiermemory/openai-api-key"
G "$ENV; export OPENAI_API_KEY=\$(cat ~/.openai-key); T=\$(dirname \$(dirname \$(find data/tasks -name task.toml | head -1))); harbor run -p \$T -a oracle -e docker -n 4 --ve GRADING_MODEL=openai/gpt-5.6-sol --jobs-dir jobs --job-name oracle-tasks -y 2>&1 | tail -6"
G "$ENV; frontier-memory score jobs/oracle-tasks 2>&1 | tail -30"
G "$ENV"'; python - <<PY
import json
from pathlib import Path
for r in sorted(Path("jobs/oracle-tasks").glob("*/result.json")):
    d=json.loads(r.read_text()); v=(d.get("verifier_result") or {}).get("rewards") or {}
    print(d.get("task_name"), v.get("reward"), (d.get("exception_info") or {}).get("exception_type",""))
PY'

step "oracle on the memory-generation task"
G "$ENV; harbor run -p build/memory-task -a oracle -e docker --jobs-dir jobs --job-name oracle-memory -y 2>&1 | tail -4"
G 'df -h / | tail -1; sudo docker images --format "{{.Size}} {{.Repository}}" | head -24 | cut -c1-90; rm -f ~/.openai-key'
step "done"
