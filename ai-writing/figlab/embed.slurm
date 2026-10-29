#!/bin/bash
# DINOv2 embeddings of every extracted figure, one shard per array task (GPU).
#SBATCH --job-name=figlab-embed
#SBATCH --partition=all
#SBATCH --account=allcs
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --array=0-31%8
#SBATCH --output=/n/fs/resemble/cs-atlas/work/ai-writing/figlab/logs/embed-%A_%a.out
cd /n/fs/resemble/cs-atlas/work/ai-writing/figlab
export HF_HOME=/n/fs/resemble/cs-atlas-env/hf-cache HF_HUB_OFFLINE=1
# compute nodes have no ~/.triton/cache, and transformers' import of DINOv2 fails without one (2026-10-28)
export TRITON_CACHE_DIR=${TMPDIR:-/tmp}/triton-$USER-$SLURM_JOB_ID; mkdir -p $TRITON_CACHE_DIR
export LD_LIBRARY_PATH=/n/fs/resemble/cs-atlas-env/py310/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
/n/fs/resemble/cs-atlas-env/py310/bin/python -u embed.py --shard $SLURM_ARRAY_TASK_ID --batch 128
