#!/bin/bash
# verify.py / audit.py on an A6000 pair (TP=2). CMD="verify.py run --shard 2 --tag pilot4-tp2 --out-tag v1" sbatch ver_gpu.slurm
#SBATCH --job-name=sum14b-ver
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --gres=gpu:a6000:2
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=00:59:00
#SBATCH --exclude=node206
#SBATCH --output=/n/fs/resemble/homogenizing-science/studies/homogenization/work/summaries14b-20261123/logs/ver-%j.out
set -uo pipefail
. /n/fs/resemble/homogenizing-science/code/paths.sh || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=8
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false VLLM_USE_V1=${SUM_V1:-1} SUM_TP=2
export TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID} TMPDIR=/tmp/sum14b-${SLURM_JOB_ID}; mkdir -p $TMPDIR; trap 'rm -rf $TMPDIR $TRITON_CACHE_DIR' EXIT
cd /n/fs/resemble/homogenizing-science/worktrees/summaries-14b/ai-writing/summaries
nvidia-smi --query-gpu=name,memory.used --format=csv,noheader
used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | sort -n | tail -1)
[ "${used:-0}" -lt 2000 ] || { echo "{\"refused_gpu\": \"$(hostname)\"}"; exit 3; }
$CS_ATLAS_ENV_PY -u $CMD
