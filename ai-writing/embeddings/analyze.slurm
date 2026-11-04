#!/bin/bash
# Analyses on the embeddings (CPU or one 2080): analyze.slurm novelty|bertopic|entropy <model> [kind]
#   novelty: novelty_run.py --model M --kind K        bertopic: topics.py bertopic --model M        entropy: topics.py entropy --model M (M may be openalex)
# Heavy (UMAP/HDBSCAN on ~100k abstracts, pairwise cosines): Slurm only, never the login host.
#SBATCH --job-name=emb-analyze
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node105
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/emb-analyze-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" HF_HOME=$CS_ATLAS_HF_HOME NUMBA_NUM_THREADS=16 OMP_NUM_THREADS=16
cd "$CS_ATLAS_AI_WRITING/embeddings"
case "${1:?novelty|bertopic|entropy}" in
  novelty) $CS_ATLAS_ENV_PY -u novelty_run.py --model "${2:?model}" --kind "${3:-abstract}" ;;
  bertopic) $CS_ATLAS_ENV_PY -u topics.py bertopic --model "${2:?model}" ;;
  entropy) $CS_ATLAS_ENV_PY -u topics.py entropy --model "${2:?model}" ;;
esac
