#!/bin/bash
# Incremental passage scoring with the final model (no retraining): the store of not-yet-scored texts built by
# score_delta_prep.py (data/delta-<tag>.sqlite) is copied to node-local /tmp and scored in N array shards;
# outputs results/scores/shard-<tag>-<i>.jsonl.gz and papers-<tag>-<i>.jsonl.gz beside the full run's shards.
# usage: sbatch --array=0-$((N-1)) score_delta.slurm TAG N
#SBATCH --job-name=aiw2-detdelta
#SBATCH --partition=all
#SBATCH --account=allcs
#SBATCH --gres=gpu:a5000:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=00:59:00
#SBATCH --output=/n/fs/resemble/cs-atlas/work/ai-writing/detector_v2/logs/detdelta-%A_%a.out
set -euo pipefail
TAG=$1; N=$2; I=${SLURM_ARRAY_TASK_ID}
PY=/n/fs/resemble/cs-atlas-env/py310/bin/python
D=/n/fs/resemble/cs-atlas/work/ai-writing/detector_v2
cd $D
export LD_LIBRARY_PATH="/n/fs/resemble/cs-atlas-env/py310/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=/n/fs/resemble/cs-atlas-env/hf-cache HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
L=/tmp/aiw2-detdelta-${SLURM_JOB_ID}; mkdir -p $L; trap 'rm -rf "$L"' EXIT
export TRITON_CACHE_DIR=$L/triton  # ~/.triton/cache is absent on the nodes (job 32014579 failed on it)
cp data/delta-$TAG.sqlite $L/delta.sqlite
echo "{\"node\": \"$(hostname)\", \"tag\": \"$TAG\", \"shard\": $I, \"of\": $N, \"gpus\": \"${CUDA_VISIBLE_DEVICES:-}\"}"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
$PY -u -B detector.py score --shard "$I" --nshards "$N" --db $L/delta.sqlite --name "$TAG-$I" 2>&1 | { grep -v -E "tensorflow|cudart|dso_loader" || true; }
