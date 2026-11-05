#!/bin/bash
set -euo pipefail
source official/vm/lib-cluster2.sh
vm_boot 6 20G
ENV='cd ~/official/frontiermemory && . .venv/bin/activate'
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
python3 - <<PY
import hashlib
from pathlib import Path

left, right = Path("data/tasks/frontier-memory"), Path("data/tasks-fm")

def files(root):
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*") if p.is_file()
    }

a, b = files(left), files(right)
changed = sorted(path for path in a.keys() | b.keys() if a.get(path) != b.get(path))
expected = ["cookie-store-compositional-changelog/tests/Dockerfile"]
print(f"task-copy-files={len(a)} task-copy-differences={len(changed)}")
if changed != expected:
    print("TASK_COPY_CHECK_FAILED")
    raise SystemExit(1)
print("TASK_COPY_CHECK_OK cookie-store-compositional-changelog")
PY'
