#!/bin/bash
# The exploratory arms (results/preregistration-arms.md) in one held allocation, after the preregistered study's job has
# ended. Same resources and job name as run-all.sbatch, so --dependency=singleton queues it behind that job.
#   sbatch --dependency=singleton official/vm/run-arms.sbatch            all arms, in the preregistered order
#   sbatch --dependency=singleton --export=ALL,ARMS="placebo readfirst" official/vm/run-arms.sbatch
#   sbatch --dependency=singleton --export=ALL,STAGE=checks official/vm/run-arms.sbatch   checks only, about a day
#SBATCH --job-name=fm-serial
#SBATCH --partition=vcggpu
#SBATCH --nodelist=nodevcggpu02
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=12
#SBATCH --mem=64G
#SBATCH --time=14-00:00:00
#SBATCH --output=official/logs/set-%j.log
bash official/vm/next-study-3.sh
