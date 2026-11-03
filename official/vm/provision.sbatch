#!/bin/bash
# Set up the Docker guest after build-and-test-vm.sbatch: official tools, corpus v1.1, tasks, task copy with the cookie-store repair (D72), Word2Vec image (D71), repeated checks. CPU only.
#SBATCH --job-name=fm-provision
#SBATCH --partition=vcggpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --output=official/logs/provision-%j.log
set -uo pipefail
REPO=$PWD; source official/vm/lib.sh
step() { echo; echo "=== $(date +%m-%d\ %H:%M:%S) $*"; }
vm_boot 6 20G || exit 1
G() { "${SSH[@]}" "$@"; }
step "official tools at upstream 9af28c2"
G 'set -e; sudo apt-get -qq update; sudo apt-get -qq -y install python3-venv git >/dev/null 2>&1; mkdir -p ~/official; cd ~/official; git clone -q https://github.com/letta-ai/frontiermemory; cd frontiermemory; git checkout -q 9af28c2f8210779f442aa36a1d73553630441af5; git log --oneline -1; python3 -m venv ~/boot; ~/boot/bin/pip -q install uv==0.11.21; ~/boot/bin/uv -q venv --python 3.12; . .venv/bin/activate; ~/boot/bin/uv -q pip install -e .; python --version; harbor --version' || { echo PROVISION_FAILED; exit 1; }
step "corpus v1.1"
G 'mkdir -p ~/official/frontiermemory/data/corpus'; "${SCP[@]}" "$REPO/data/corpus/v1.1" fm@127.0.0.1:official/frontiermemory/data/corpus/
ENV='cd ~/official/frontiermemory && . .venv/bin/activate'
G "$ENV; python -c \"from pathlib import Path; from frontier_memory.corpus import verify_corpus; print('digest', verify_corpus(Path('data/corpus/v1.1')))\"" || { echo PROVISION_FAILED; exit 1; }
step "tasks, with checksums"
G "$ENV; harbor dataset download letta-ai/frontier-memory@v1.0 -o data/tasks 2>&1 | tail -1"
G "$ENV"'; python - <<PY
import json
from pathlib import Path
from dirhash import dirhash
want=json.load(open("tasks.json"))["release"]; bad=0; n=0
for t in sorted(Path("data/tasks").rglob("task.toml")):
    n+=1; bad+= want.get(t.parent.name)!=dirhash(t.parent,"sha256")
print(n,"tasks,",bad,"checksum mismatches"); raise SystemExit(bad>0 or n!=15)
PY' || { echo PROVISION_FAILED; exit 1; }
step "task copy with the one cookie-store line (D72)"
G 'cd ~/official/frontiermemory; cp -r data/tasks/frontier-memory data/tasks-fm; python3 - <<PY
from pathlib import Path
p=Path("data/tasks-fm/cookie-store-compositional-changelog/tests/Dockerfile"); s=p.read_text()
a="        click==8.1.8 \\\\\n        socksio==1.0.0"
assert s.count(a)==1
p.write_text(s.replace(a,"        click==8.1.8 \\\\\n        anyio==4.15.1 \\\\\n        socksio==1.0.0"))
PY
diff -r data/tasks/frontier-memory data/tasks-fm; true'
step "Word2Vec image from the unmodified task (D71)"
G 'cd ~/official/frontiermemory; S=$(date +%s); sudo docker build -q -t fm-w2v-cache data/tasks/frontier-memory/build-word2vec-pipeline/environment 2>&1 | tail -1 | cut -c1-90; echo "build took $(( $(date +%s)-S )) s"; sudo docker images fm-w2v-cache --format "{{.ID}} {{.Size}}"; df -h / | tail -1'
step "network probe, reference solution on Word2Vec"
G "$ENV; sudo env PATH=\$PATH harbor run -p data/tasks-fm -a oracle -e docker -n 1 -i 'build-word2vec*' --jobs-dir jobs --job-name oracle-w2v -y 2>&1 | tail -1 | cut -c1-100; sudo chown -R fm:fm jobs; python3 -c \"
import json,glob
for r in glob.glob('jobs/oracle-w2v/*/result.json'):
    d=json.load(open(r)); print((d.get('verifier_result') or {}).get('rewards'),(d.get('exception_info') or {}).get('exception_type',''))\""
step "PROVISION_DONE"
