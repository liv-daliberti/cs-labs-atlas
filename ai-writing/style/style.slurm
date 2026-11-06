#!/bin/bash
# Writing-style study: sbatch style.slurm extract {abstract|allai|fulltext}   |   sbatch style.slurm analyze {abstract|fulltext}   |   sbatch style.slurm report
#SBATCH --job-name=style
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --time=00:59:00
#SBATCH --output=/n/fs/resemble/homogenizing-science/scratch/lineage-style/logs/style-%j.out
# Paths by environment (style_common.py): STYLE_OUT, STYLE_TAG, STYLE_AI, STYLE_FULLTEXT_DB. extract is resumable (finished chunks are skipped).
set -euo pipefail
HERE=${STYLE_CODE:-${SLURM_SUBMIT_DIR:?}}
. "$HERE/../../paths.sh"
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
cd "$HERE"
case "${1:?extract|analyze|report}" in
  extract) $CS_ATLAS_ENV_PY -u style_extract.py "${2:?source}" --procs 16 ;;
  analyze) $CS_ATLAS_ENV_PY -u style_analyze.py --kind "${2:?kind}" --model "${STYLE_TOPIC_MODEL:-specter2_proximity}" ;;
  report) $CS_ATLAS_ENV_PY -u style_report.py ;;
esac
