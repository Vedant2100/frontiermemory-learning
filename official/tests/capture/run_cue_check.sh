#!/bin/bash
# D134: does the cue arm's plugin load in the pinned Hermes and do what the arm claims? Synthetic memory only; no GPU, no key.
# Setup once: the pinned Hermes in $FM_HERMES_PIN (see run_capture.sh). Prints booleans and sizes.
set -u
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../../.." && pwd); PIN=${FM_HERMES_PIN:-$HOME/.cache/fm-hermes-pin}
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; H=$T/home; mkdir -p "$H/plugins" "$T/log" "$T/memory/skills/synthetic-check"
printf '# Learned Hermes skills\n- synthetic-check\n' > "$T/memory/MEMORY.md"
printf -- '---\nname: synthetic-check\ndescription: Check the synthetic widget before shipping.\n---\nSYNTHETIC-SKILL-BODY\n' > "$T/memory/skills/synthetic-check/SKILL.md"
cp -r "$REPO/official/fm_local/cue_plugin" "$H/plugins/fm-cue"; cp "$REPO/official/fm_local/arm_logic.py" "$H/plugins/fm-cue/arm_logic.py"
printf 'plugins:\n  enabled: [fm-cue]\nmemory:\n  memory_enabled: false\n' > "$H/config.yaml"
cd "$PIN/source" && env -i PATH=/usr/bin:/bin HOME="$T" HERMES_HOME="$H" FM_CUE_MEMORY="$T/memory" FM_CUE_LOG="$T/log" "$PIN/venv/bin/python" - <<'PY'
import json, os, sys
sys.path.insert(0, ".")
from hermes_cli.plugins import discover_plugins
from hermes_cli.lifecycle import has_hook, invoke_hook
discover_plugins(force=True)
kw = dict(duration_ms=1, status="ok", error_type=None, error_message=None)
def call(cmd): return [x for x in invoke_hook("transform_tool_result", tool_name="terminal", args={"command": cmd}, result="plain", **kw) if isinstance(x, str)]
unrelated = call("ls /workspace")
first = call("echo synthetic-check widget")  # the first matching call
second = call("echo synthetic-check widget")  # the same skill again
ok = {"hook registered": has_hook("transform_tool_result"),
      "unrelated call leaves the result alone": not unrelated,
      "matching call appends the skill text": bool(first) and "SYNTHETIC-SKILL-BODY" in first[0] and first[0].startswith("plain"),
      }
m = json.load(open(os.environ["FM_CUE_LOG"] + "/fm-cue-metrics.json"))
ok["a second matching call appends nothing"] = not second
ok["metrics: 1 skill, 1 activation"] = m["skills"] == 1 and m["activations"] == 1
for k, v in ok.items(): print(("PASS " if v else "FAIL ") + k)
sys.exit(0 if all(ok.values()) else 1)
PY
