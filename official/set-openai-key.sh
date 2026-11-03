#!/bin/bash
# Ask for the OpenAI key used by the official APEX judge and save it outside the repo, readable only by you.
# The key is not echoed, printed or passed on any command line.
set -euo pipefail
KEY_FILE="${HOME}/.config/frontiermemory/openai-api-key"

read -r -s -p "OpenAI API key (hidden): " key
echo
[ -n "$key" ] || { echo "Nothing entered; no change made." >&2; exit 1; }

umask 077
mkdir -p "$(dirname "$KEY_FILE")"
printf '%s\n' "$key" > "$KEY_FILE"
chmod 600 "$KEY_FILE"
unset key
echo "Saved to $KEY_FILE ($(wc -c < "$KEY_FILE" | tr -d ' ') bytes, mode $(stat -c %a "$KEY_FILE"))."
