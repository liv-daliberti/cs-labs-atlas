#!/bin/bash
# ROADMAP #51: one UTC day of the trickled 2016-2024 OpenAlex re-pull (tools/oa_repull_trickle.py): chunks of one (school, year), at most 2,000 credits,
# never writing a store while a cs-release job runs; it resubmits itself (--begin next UTC day, or behind a release) until all 81 chunks are done.
#   first run:  sbatch --dependency=afterany:<release job> --export=ALL,CS_ATLAS_SNAPSHOT_COMMIT=<sha> tools/oa_repull_trickle.slurm   (from the main checkout)
# One network-bound stream (~1.2 s a request): 1 CPU. Merge holds one school-year of works in memory.
#SBATCH --job-name=cs-repull
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=06:00:00
#SBATCH --output=fulltext-push/logs/oa-repull-trickle-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
# shellcheck disable=SC2086
"$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/oa_repull_trickle.py" run ${REPULL_ARGS:-}
