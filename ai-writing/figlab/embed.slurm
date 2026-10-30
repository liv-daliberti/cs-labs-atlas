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
#SBATCH --output=ai-writing/figlab/logs/embed-%A_%a.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd ${CS_ATLAS_AI_WRITING}/figlab
export HF_HOME=${CS_ATLAS_HF_HOME} HF_HUB_OFFLINE=1
# compute nodes have no ~/.triton/cache, and transformers' import of DINOv2 fails without one (2026-10-28)
export TRITON_CACHE_DIR=${TMPDIR:-/tmp}/triton-$USER-$SLURM_JOB_ID; mkdir -p $TRITON_CACHE_DIR
export LD_LIBRARY_PATH=${CS_ATLAS_ENV_LIB}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
${CS_ATLAS_ENV_PY} -u embed.py --shard $SLURM_ARRAY_TASK_ID --batch 128
