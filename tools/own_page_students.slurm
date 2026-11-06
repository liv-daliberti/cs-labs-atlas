#!/bin/bash
#SBATCH --job-name=own-page-students
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:55:00
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --output=%x-%j.out
# usage: sbatch --export=ALL,CS_ATLAS_SNAPSHOT_COMMIT=<sha>,SNAPSHOT_REPO=<worktree>,OPS_ARGS="dblp gatech uchicago michigan" tools/own_page_students.slurm
#        OPS_ARGS="fetch gatech --shard 0/8" (one shard per array task; the fetch paces itself per host: 3 s or the Crawl-delay)
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
cd "$CS_ATLAS_CODE"
$CS_ATLAS_PY -u "$CS_ATLAS_TOOLS/own_page_students.py" ${OPS_ARGS:?}
