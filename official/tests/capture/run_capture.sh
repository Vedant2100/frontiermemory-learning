#!/bin/bash
# Setup (once): the pinned Hermes in $FM_HERMES_PIN, installed as frontier_memory/agents/hermes.py install_runtime does
# (git fetch d923a5eb; uv venv --python 3.14; uv pip install -e "source[anthropic,mcp]"). No GPU, no key, no study data.
# Check (a), D128: does pinned Hermes d923a5eb put the config's agent.system_prompt into the system text of its model
# requests, when run the way the adapter runs it (hermes --yolo chat -Q --model M --provider openai-api -q "...",
# HERMES_HOME with config.yaml, OPENAI_BASE_URL, LocalHermes's watchdogs)? Three cases, synthetic memory only:
#   readfirst  the read-first trial's own hermes-config.yaml (Nov 7, fm-smoke-arm-readfirst), base URL -> stand-in server
#   all        that config with agent.system_prompt = exposure_hermes.injected_text(synthetic memory) (the all arm)
#   control    that config with agent.system_prompt removed (HM): markers must be absent
set -u
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../../.." && pwd)
HERMES=${FM_HERMES_PIN:-$HOME/.cache/fm-hermes-pin}/venv/bin/hermes; OUT=${OUT:-$(mktemp -d)}; rm -rf "$OUT"; mkdir -p "$OUT"
RF=$("$REPO/.venv/bin/python" -c "import sys; sys.path.insert(0,'$REPO/official/fm_local'); import arm_logic; print(arm_logic.READ_FIRST)")
MEM=$OUT/mem; mkdir -p "$MEM/skills/synthetic-check"
printf '# Learned Hermes skills\n- synthetic-check: SYNTHETIC-MEMORY-INDEX-LINE for the capture test\n' > "$MEM/MEMORY.md"
printf -- '---\nname: synthetic-check\ndescription: synthetic skill for the capture test\n---\nSYNTHETIC-SKILL-BODY-LINE only in the all arm\n' > "$MEM/skills/synthetic-check/SKILL.md"
for case in readfirst all control; do
  H=$OUT/home-$case; mkdir -p "$H/memories" "$H/skills"; cp "$MEM/MEMORY.md" "$H/memories/"; cp -r "$MEM/skills/synthetic-check" "$H/skills/"
  "$REPO/.venv/bin/python" - "$HERE/readfirst-config.yaml" "$H/config.yaml" "$case" "$MEM" "$REPO/official" <<'PY'
import sys, yaml
sys.path.insert(0, sys.argv[5])
cfg = yaml.safe_load(open(sys.argv[1])); case = sys.argv[3]
if case == "all":
    from fm_local.exposure_hermes import injected_text
    from pathlib import Path
    cfg["agent"]["system_prompt"] = injected_text(Path(sys.argv[4]))
elif case == "control":
    cfg["agent"].pop("system_prompt", None)
open(sys.argv[2], "w").write(yaml.safe_dump(cfg))
PY
  PORT=$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')
  python3 "$HERE/capture_server.py" "$PORT" "$OUT/$case.jsonl" "$RF" "SYNTHETIC-SKILL-BODY-LINE" "SYNTHETIC-MEMORY-INDEX-LINE" "synthetic-check" & SRV=$!
  sleep 1
  ( cd "$OUT" && env -i PATH=/usr/bin:/bin HOME="$H" HERMES_HOME="$H" TERMINAL_ENV=local OPENAI_API_KEY=placeholder-not-a-key \
      OPENAI_BASE_URL="http://127.0.0.1:$PORT/v1" HERMES_CODEX_TTFB_TIMEOUT_SECONDS=900 HERMES_CODEX_EVENT_STALE_TIMEOUT_SECONDS=900 \
      HERMES_API_CALL_STALE_TIMEOUT=1800 timeout 180 "$HERMES" --yolo chat -Q --model qwen3.8:27b-mtp-q4_K_M --provider openai-api \
      -q "Reply with the single word ok." > "$OUT/$case.hermes.txt" 2>&1 )
  echo "$case: hermes exit $?, requests $(wc -l < "$OUT/$case.jsonl" 2>/dev/null || echo 0)"
  kill $SRV 2>/dev/null; wait $SRV 2>/dev/null
  head -1 "$OUT/$case.jsonl" 2>/dev/null
done
