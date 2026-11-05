#!/bin/bash
# Log, every 15 seconds, whether any container's config holds the real judge key. Counts only.
set -euo pipefail
umask 077
[ -s /home/fm/.judge-key ] || { echo JUDGE_KEY_MISSING; exit 1; }
cycles=0
containers_seen=0
tmp=
cleanup() {
  rm -f "${tmp:-}"
  echo "AUDIT_DONE cycles=$cycles containers_seen=$containers_seen"
}
trap cleanup EXIT
while true; do
  containers=$(sudo docker ps -q)
  count=$(printf '%s\n' "$containers" | sed '/^$/d' | wc -l)
  cycles=$((cycles + 1))
  containers_seen=$((containers_seen + count))
  echo "$(date +%H:%M) AUDIT_SAMPLE containers=$count"
  for c in $containers; do
    tmp=$(mktemp /tmp/fm-c2-key-audit.XXXXXX)
    sudo docker inspect --format '{{.Name}}|{{range .Config.Env}}{{println .}}{{end}}' "$c" > "$tmp"
    matches=$(grep -acF -f /home/fm/.judge-key "$tmp" || true)
    name=$(head -1 "$tmp" | cut -d'|' -f1 | sed -E 's/__[a-z0-9]{7}__/__/')
    rm -f "$tmp"; tmp=
    echo "$(date +%H:%M) $name real_key_lines=$matches"
    [ "$matches" = 0 ] || { echo AGENT_KEY_LEAK; exit 1; }
  done
  for _ in $(seq 1 15); do sleep 1; done
done
