#!/bin/bash
# One-off: Qwen2.5-7B-Instruct into env/hf-cache (it was not in the cache on 2026-11-04). Network + ~15 GB sequential writes; no GPU.
#SBATCH --job-name=allai-dl
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node105
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/allai-dl-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" HF_HOME=$CS_ATLAS_HF_HOME
$CS_ATLAS_ENV_PY -u -c "
from huggingface_hub import snapshot_download
p = snapshot_download('Qwen/Qwen2.5-7B-Instruct', allow_patterns=['*.json', '*.txt', '*.safetensors', 'merges.txt', 'vocab.*', 'tokenizer*'])
print(p)"
