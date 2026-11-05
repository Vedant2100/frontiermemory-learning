#!/bin/bash
set -euo pipefail
source official/vm/lib-cluster2.sh
vm_boot 6 20G
step 'diagnostic Word2Vec build with bounded duration'
G 'cd ~/official/frontiermemory; timeout --signal=TERM --kill-after=15s 300 sudo docker build --progress=plain -t fm-w2v-cache data/tasks/frontier-memory/build-word2vec-pipeline/environment'
