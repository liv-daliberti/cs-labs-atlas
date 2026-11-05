#!/bin/bash
# Fold the finished parts of the rewrite stores into their school containers: merge.slurm <style> <model> [<model> ...]  (CPU only).
#SBATCH --job-name=allai-merge
#SBATCH --partition=all
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/allai-merge-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "$CS_ATLAS_AI_WRITING/embeddings"
style=$1; shift; suf=__allai; [ "$style" = polish ] || suf=__para
for m in "$@"; do $CS_ATLAS_ENV_PY -u embed.py merge --model "$m" --kind abstract --store-name "${m}${suf}"; done
