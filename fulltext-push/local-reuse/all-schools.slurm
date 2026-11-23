#!/bin/bash
# LR_SCHOOLS="hit michigan ..." atlas submit fulltext-push/local-reuse/all-schools.slurm
# Isolated cross-catalog inventory: no legacy disk harvest is replaced. Restarting
# rechecks current missing works; successful imports and attempts remain recorded.
#SBATCH --job-name=localreuse-all
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:59:00
#SBATCH --signal=B:USR1@900
#SBATCH --output=fulltext-push/logs/localreuse-all-%j.out
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
. "$CS_ATLAS_CODE/fulltext-push/loop_job.sh"
refuse_if_downloads_stopped
export LR_SCHOOLS="${LR_SCHOOLS:-all}" LR_SOURCE_SCHOOLS="${LR_SOURCE_SCHOOLS:-all}"
export CS_ATLAS_FT_LOCAL_REUSE="${LR_DATA:-$CS_ATLAS_SCRATCH/local-reuse-all-schools}"
mkdir -p "$CS_ATLAS_FT_LOCAL_REUSE" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH/local-reuse" || exit 1
RESTART_LOG="$CS_ATLAS_FT_LOGS/localreuse-all.restarts"
reuse_pass() {
    # Forward TERM to the current Python process before releasing the run lock.
    trap 'kill -TERM "$child" 2>/dev/null; wait "$child"; exit 143' TERM INT
    exec 7>"$CS_ATLAS_FT_LOCAL_REUSE/.run.lock"
    flock -n 7 || exit 0
    for stage in snapshot plan import; do
        script=reuse_import.py
        [ "$stage" = snapshot ] && script=lr_common.py
        "$CS_ATLAS_COLLECTOR_PY" -I -u "$script" "$stage" &
        child=$!
        wait "$child" || exit $?
    done
    schools=$("$CS_ATLAS_COLLECTOR_PY" -I lr_common.py schools) || exit 1
    "$CS_ATLAS_COLLECTOR_PY" -I -u "$CS_ATLAS_TOOLS/lab_paper_copies.py" $schools &
    child=$!
    wait "$child"
}
export -f reuse_pass
run_restartable fulltext-push/local-reuse/all-schools.slurm -- bash -c reuse_pass
