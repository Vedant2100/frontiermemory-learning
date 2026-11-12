#!/bin/bash
# Read-only: boot the finished guest on its node, print per-trial hidden-test partial credit for the blend arm, power off. CPU only, no GPU.
#SBATCH --job-name=fm-extract
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu02
#SBATCH --cpus-per-task=3
#SBATCH --mem=10G
#SBATCH --time=00:30:00
#SBATCH --output=official/logs/extract-blend-%j.log
source official/vm/lib.sh; vm_boot 2 6G || exit 1
echo EXTRACT_BEGIN
G 'sudo python3 - extract /home/fm/official/frontiermemory/jobs fm-tasks-arm-blend' < scripts/partial_credit.py
echo EXTRACT_END
vm_stop; trap - EXIT
