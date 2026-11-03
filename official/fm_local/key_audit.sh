#!/bin/bash
# Log, every minute, whether any container's config holds the real judge key. Counts only.
while true; do
  for c in $(sudo docker ps -q); do
    sudo docker inspect --format '{{.Name}}|{{range .Config.Env}}{{println .}}{{end}}' "$c" > /tmp/ka.$$
    echo "$(date +%H:%M) $(head -1 /tmp/ka.$$ | cut -d'|' -f1 | sed -E 's/__[a-z0-9]{7}__/__/') real_key_lines=$(grep -cF "$(cat ~/.judge-key)" /tmp/ka.$$)"
  done
  rm -f /tmp/ka.$$; sleep 60
done
