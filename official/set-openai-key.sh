#!/bin/bash
# Ask for the APEX judge key, check it with the provider, and save it outside the repo, readable only by you.
# Usage: official/set-openai-key.sh [openai|anthropic]   (default openai)
# The key is never echoed, printed or put on a command line. A key the provider rejects is not saved.
set -euo pipefail
PROVIDER="${1:-openai}"
case "$PROVIDER" in
  openai)    KEY_FILE="$HOME/.config/frontiermemory/openai-api-key"; URL=https://api.openai.com/v1/models; WANT=gpt-5.6-sol ;;
  anthropic) KEY_FILE="$HOME/.config/frontiermemory/anthropic-api-key"; URL=https://api.anthropic.com/v1/models; WANT= ;;
  *) echo "Unknown provider '$PROVIDER': use openai or anthropic." >&2; exit 2 ;;
esac

read -r -s -p "$PROVIDER API key (hidden): " key
echo
key="$(printf '%s' "$key" | tr -d '[:space:]')"
[ -n "$key" ] || { echo "Nothing entered; no change made." >&2; exit 1; }

body="$(mktemp)"; trap 'rm -f "$body"' EXIT
if [ "$PROVIDER" = openai ]; then
  code="$(printf 'header = "Authorization: Bearer %s"\n' "$key" | curl -s -m 25 -o "$body" -w '%{http_code}' -K - "$URL")" || code=000
else
  code="$(printf 'header = "x-api-key: %s"\nheader = "anthropic-version: 2023-06-01"\n' "$key" | curl -s -m 25 -o "$body" -w '%{http_code}' -K - "$URL")" || code=000
fi
if [ "$code" != 200 ]; then
  echo "Rejected (HTTP $code); nothing saved. Check the key was copied whole and is active." >&2
  exit 1
fi

umask 077
mkdir -p "$(dirname "$KEY_FILE")"
printf '%s\n' "$key" > "$KEY_FILE"
chmod 600 "$KEY_FILE"
unset key
echo "Accepted and saved to $KEY_FILE."
if [ -n "$WANT" ]; then
  if grep -q "\"$WANT\"" "$body"; then echo "Judge model $WANT is available on this key."
  else echo "WARNING: judge model $WANT is NOT listed for this key. Tell Claude." >&2; fi
fi
