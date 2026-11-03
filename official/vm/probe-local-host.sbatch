#!/bin/bash
# CPU only. Does Harbor's restriction allow a task to reach a server on the VM host at 10.0.2.2, and still block other hosts? Also checks the adapter imports.
#SBATCH --job-name=fm-probe2
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu01
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=official/logs/probe2-%j.log
REPO=$PWD; source official/vm/lib.sh; PORT=$(free_port)
D=$(mktemp -d); echo served > "$D/ok"; (cd "$D" && exec python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1) & WEB=$!
vm_boot 3 6G || exit 1
"${SSH[@]}" 'mkdir -p ~/official'; "${SCP[@]}" "$REPO/official/fm_local" fm@127.0.0.1:official/
"${SSH[@]}" "cd ~/official/frontiermemory; . .venv/bin/activate; PYTHONPATH=~/official FM_LOCAL_BASE_URL=http://10.0.2.2:$PORT/v1 python -c 'import fm_local.hermes_local as h; print(\"adapter import OK\", h.base_url())'
sudo env PATH=\$PWD/.venv/bin:\$PATH harbor run -p build/memory-task -a frontier_memory.agents.probe:NetworkProbe -e docker --allow-agent-host 10.0.2.2 --ak 'urls=[\"http://10.0.2.2:$PORT/ok\",\"https://example.com\",\"https://api.openai.com\"]' --jobs-dir jobs --job-name probe-local -y 2>&1 | tail -1 | cut -c1-120
sudo find jobs/probe-local -name network-probe.json -exec cat {} \; ; sudo rm -rf jobs/probe-local" 2>&1
kill $WEB; rm -rf "$D"
