#!/bin/bash
#SBATCH --job-name=cs-related-candidates
#SBATCH --partition=all
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --time=00:55:00
#SBATCH --output=hierarchy/logs/cs-related-candidates-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1  # code of one commit, data in the main checkout (docs/CONTRIBUTING.md); submit with `atlas submit`
cd "$CS_ATLAS_WORK"
/usr/bin/time -v ${CS_ATLAS_PY} -u "$CS_ATLAS_TOOLS"/cs_related_candidates.py "$@"
