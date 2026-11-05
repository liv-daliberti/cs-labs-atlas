#!/bin/bash
# embed.py status (papers todo / done per model and kind) as a CPU job: it takes minutes, so never on the login host.   sbatch status.slurm [--model M]
#SBATCH --job-name=emb-status
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node105
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/emb-status-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "$CS_ATLAS_AI_WRITING/embeddings"
$CS_ATLAS_ENV_PY -u embed.py status "$@"
