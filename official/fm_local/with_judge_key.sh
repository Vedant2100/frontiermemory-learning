#!/bin/bash
# Run a command with the judge key in its environment, read from a file, so the key is never on a command line.
export JUDGE_ANTHROPIC_KEY="$(cat /home/fm/.judge-key)"
exec "$@"
