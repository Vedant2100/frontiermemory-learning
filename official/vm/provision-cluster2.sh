#!/bin/bash
set -euo pipefail
source official/vm/lib-cluster2.sh
vm_boot 6 20G
step 'official tools at upstream 9af28c2'
G 'set -e; sudo apt-get -qq update; sudo apt-get -qq -y install python3-venv git >/dev/null 2>&1; mkdir -p ~/official; cd ~/official; test ! -e frontiermemory; git clone -q https://github.com/letta-ai/frontiermemory; cd frontiermemory; git checkout -q 9af28c2f8210779f442aa36a1d73553630441af5; git log --oneline -1; python3 -m venv ~/boot; ~/boot/bin/pip -q install uv==0.11.21; ~/boot/bin/uv -q venv --python 3.12; . .venv/bin/activate; ~/boot/bin/uv -q pip install -e .; python --version; harbor --version'
