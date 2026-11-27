#!/bin/bash
#SBATCH --job-name=ftadv-build
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=3
#SBATCH --mem=40G
#SBATCH --time=00:59:00
#SBATCH --exclude=node302,node014
#SBATCH --output=hierarchy/logs/ftadv-build-%A_%a.log
# Trial builds (PI_HIERARCHY_OUT, nothing live is written): index = 2*school_index + variant; variant 0 = main's reviewed files, 1 = this branch's overlay root.
# usage: WT=<worktree> OUT=<scratch dir> sbatch --array=0-9 tools/ft-adv-trial-build.slurm
set -euo pipefail
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh"
SNAPSHOT_REPO="$WT" . "$CS_ATLAS_CODE/tools/job_code_snapshot.sh"
SCHOOLS=(gatech uchicago mit cmu epfl)
i=$SLURM_ARRAY_TASK_ID; s=${SCHOOLS[$((i/2))]}; v=$((i%2))
export CS_ATLAS_THROTTLE_STATE="$CS_ATLAS_CODE/fulltext-push/raw/host-throttle.json"
if [ "$v" = 1 ]; then export CS_ATLAS_CODE="$(cs_atlas_school_dir "$s" tmp "$WT")/overlay"; PI_HIERARCHY_OUT="$OUT/after"; else PI_HIERARCHY_OUT="$OUT/before"; fi
export PI_HIERARCHY_OUT; mkdir -p "$PI_HIERARCHY_OUT"
cd "$CS_ATLAS_CODE"
nice -n10 "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/pi_hierarchy.py" "$s"
