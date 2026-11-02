#!/bin/bash
# `atlas release` as one Slurm job (ROADMAP #37): the chain rebuild -> validate -> regression -> reader -> release -> tree -> export, stopping at the first
# failure. The steps that publish outside this host are not part of it unless you pass the flags: sbatch --export=ALL,RELEASE_ARGS="--yes-push --yes-hf"
# (default: they stop with exit status 3 and the run resumes with `atlas release --resume --yes-push`). Submit with `atlas submit`; check with --test-only.
#SBATCH --job-name=cs-release
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --time=06:00:00
#SBATCH --output=hierarchy/logs/release-%j.out
set -u
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # submit from the code root
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1  # code of one commit, data in the main checkout (docs/CONTRIBUTING.md)
cd "$CS_ATLAS_WORK"
exec "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/atlas_release.py" --tag "release-$SLURM_JOB_ID" ${RELEASE_ARGS:-}
