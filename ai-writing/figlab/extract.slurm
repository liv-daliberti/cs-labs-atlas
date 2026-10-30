#!/bin/bash
# Figure extraction for the figures -> lab classifier: one manifest shard per array task (CPU).
#SBATCH --job-name=figlab-extract
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=06:00:00
#SBATCH --array=0-31%16
#SBATCH --output=ai-writing/figlab/logs/extract-%A_%a.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd ${CS_ATLAS_AI_WRITING}/figlab
${CS_ATLAS_ENV_PY} -u extract.py --shard $SLURM_ARRAY_TASK_ID --of 32
