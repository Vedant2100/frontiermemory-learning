#!/bin/bash
set -euo pipefail
source official/vm/lib-cluster2.sh
vm_boot 4 12G
G 'set -e; test ! -e /etc/docker/daemon.json; printf "{\"builder\":{\"gc\":{\"enabled\":false}}}\n" | sudo tee /etc/docker/daemon.json >/dev/null; sudo dockerd --validate --config-file=/etc/docker/daemon.json; sudo systemctl restart docker; sudo docker info --format "{{.ServerVersion}}"; echo CACHE_GC_DISABLED'
