#!/bin/bash
# Read-only: check the VM disk image and trial data are still on the node-local /scratch.
#SBATCH --job-name=fm-probe-disk
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu02
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:10:00
#SBATCH --output=results/failure-analysis/probe/probe-%j.log
hostname; date
ls -la /scratch/$USER/fm-vm 2>&1 | head -30
du -sh /scratch/$USER/fm-vm/* 2>&1 | head
df -h /scratch 2>&1 | tail -2
