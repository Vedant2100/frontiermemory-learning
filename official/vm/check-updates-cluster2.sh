#!/bin/bash
# Fail closed when main's append-only handoff changes or a known update is absent locally.
set -euo pipefail
REPO=$(realpath "$HOME/frontiermemory-cluster2")
cd "$REPO"
[ "$(git branch --show-current)" = cluster2 ] || { echo UPDATE_CHECK_WRONG_BRANCH; exit 1; }
git fetch --quiet origin || { echo UPDATE_CHECK_FETCH_FAILED; exit 1; }
git show origin/main:HANDOFF-updates.md | grep '^## U[0-9]' || { echo UPDATE_CHECK_MISSING; exit 1; }
current=$(git rev-parse origin/main:HANDOFF-updates.md)
[ "$current" = 8cea454bfe730e111d19dac04dd9649290b0c0b0 ] || { echo UPDATE_CHECK_NEW_CONTENT; exit 1; }
git merge-base --is-ancestor 024865e HEAD || { echo UPDATE_CHECK_U1_NOT_APPLIED; exit 1; }
grep -q 'D20.*D103.*Codex.*Claude Code' results/decisions-log-cluster2.md || { echo UPDATE_CHECK_U3_NOT_APPLIED; exit 1; }
grep -q 'D21.*D104.*agent-end close' results/decisions-log-cluster2.md || { echo UPDATE_CHECK_U4_NOT_APPLIED; exit 1; }
echo UPDATE_CHECK_OK
