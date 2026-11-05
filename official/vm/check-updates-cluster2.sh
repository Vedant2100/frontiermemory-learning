#!/bin/bash
# Fail closed when main's append-only handoff changes or known update content is absent locally.
set -euo pipefail
REPO=$(realpath "$HOME/frontiermemory-cluster2")
cd "$REPO"
[ "$(git branch --show-current)" = cluster2 ] || { echo UPDATE_CHECK_WRONG_BRANCH; exit 1; }
git fetch --quiet origin || { echo UPDATE_CHECK_FETCH_FAILED; exit 1; }
git show origin/main:HANDOFF-updates.md | grep '^## U[0-9]' || { echo UPDATE_CHECK_MISSING; exit 1; }
current=$(git rev-parse origin/main:HANDOFF-updates.md)
[ "$current" = 8cea454bfe730e111d19dac04dd9649290b0c0b0 ] || { echo UPDATE_CHECK_NEW_CONTENT; exit 1; }
# The GitHub API published cluster2 as a tree snapshot on e7b84fd, so the earlier
# local U1 commit is not an ancestor. Verify the imported U1 files by blob instead.
check_blob() {
  local path=$1 expected=$2 actual
  actual=$(git hash-object -- "$path") || { echo "UPDATE_CHECK_U1_FILE_MISSING:$path"; exit 1; }
  [ "$actual" = "$expected" ] || { echo "UPDATE_CHECK_U1_FILE_MISMATCH:$path"; exit 1; }
}
check_blob official/fm_local/hermes_local.py ceb450328b9ab21b7a1ac3219a034fd5948975b1
check_blob official/fm_local/model_relay.py 570b35fe352a10ecc2f824d68097b55043cc297d
check_blob official/tests/test_hermes_local.py ebc62dc40d2ff6886f1b293a31598a7f06c73b0f
check_blob official/vm/next-gate-2.sh d96e9a100de00a674f7fa3ce58a311ddb065ce3d
# Current cluster2 serving audit includes U1 watchdog and the later U4 timing rule.
check_blob official/vm/check-serving.py 1ce151d4dae0309a341610bd3c80e8e549372ae1
grep -q 'D15.*Applied U1' results/decisions-log-cluster2.md || { echo UPDATE_CHECK_U1_DECISION_MISSING; exit 1; }
grep -q 'D20.*D103.*Codex.*Claude Code' results/decisions-log-cluster2.md || { echo UPDATE_CHECK_U3_NOT_APPLIED; exit 1; }
grep -q 'D21.*D104.*agent-end close' results/decisions-log-cluster2.md || { echo UPDATE_CHECK_U4_NOT_APPLIED; exit 1; }
echo UPDATE_CHECK_OK
