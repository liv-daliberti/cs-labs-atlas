#!/bin/bash
# Lineage study, one array task per (model, kind): sbatch --array=0-12%6 lineage.slurm      (build first: sbatch lineage.slurm build)
#SBATCH --job-name=lineage
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:59:00
#SBATCH --output=/n/fs/resemble/homogenizing-science/scratch/lineage-style/logs/lineage-%A_%a.out
# Paths by environment (lineage_common.py): LINEAGE_HIER, LINEAGE_OUT, LINEAGE_TAG, LINEAGE_AI. Done tasks are skipped (outputs exist); --force redoes.
set -euo pipefail
HERE=${LINEAGE_CODE:-${SLURM_SUBMIT_DIR:?}}
. "$HERE/../../paths.sh"
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd "$HERE"
if [ "${1:-}" = build ]; then exec $CS_ATLAS_ENV_PY -u lineage_build.py; fi
JOBS=()
for m in specter2_base specter2_proximity scincl qwen3_0p6b gte_qwen2_1p5b bge_m3 nomic_v15; do JOBS+=("$m abstract"); done
for m in specter2_base specter2_proximity qwen3_0p6b gte_qwen2_1p5b bge_m3 nomic_v15; do JOBS+=("$m fulltext"); done
read -r M K <<< "${JOBS[${SLURM_ARRAY_TASK_ID:?array task}]}"
$CS_ATLAS_ENV_PY -u lineage_run.py --model "$M" --kind "$K" ${LINEAGE_ARGS:-}
