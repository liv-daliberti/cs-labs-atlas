#!/bin/bash
#SBATCH --job-name=cs-related-candidates
#SBATCH --partition=all
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --time=00:55:00
#SBATCH --output=hierarchy/logs/cs-related-candidates-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd "$CS_ATLAS_WORK"
/usr/bin/time -v ${CS_ATLAS_PY} -u tools/cs_related_candidates.py "$@"
