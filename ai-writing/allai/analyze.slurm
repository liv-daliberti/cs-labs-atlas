#!/bin/bash
# CPU analysis of one model: analyze.slurm geom|novelty <model> [style]. ALLAI_BOOT / ALLAI_DRAWS override the replicate counts (tests).
#SBATCH --job-name=allai-an
#SBATCH --partition=all
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/allai-an-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" OMP_NUM_THREADS=16 OPENBLAS_NUM_THREADS=16 MKL_NUM_THREADS=16 NUMBA_NUM_THREADS=16
cd "$CS_ATLAS_AI_WRITING/allai"
$CS_ATLAS_ENV_PY -u -B allai_analyze.py "${1:?geom|novelty}" --model "${2:?model}" --style "${3:-polish}"
