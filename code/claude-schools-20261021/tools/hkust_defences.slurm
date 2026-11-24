#!/bin/bash
# HKUST CSE event pages (R-STU-29, tools/hkust_cse_defences.py): crawl the PhD qualifying/proposal/thesis event pages through school_web.live
# (robots honoured, >= 3 s per host, stored in the school's capture store, resumable: re-submit and stored pages are skipped). One chunk <= 50 min of
# work; exit 0 = budget end or done (re-submit until 'fetched 0'), 3 = the host blocked us (403/429/401/challenge/failure burst): do NOT re-submit.
# Check with `sbatch --test-only` first; submit with `atlas submit`.
# usage: TODO=<todo.json> sbatch tools/hkust_defences.slurm
#SBATCH --job-name=hkust-defences
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --output=hierarchy/logs/hkust-defences-%j.out
set -u
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
cd "$CS_ATLAS_WORK" 2>/dev/null || cd "$CS_ATLAS_CODE"
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
"$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/hkust_cse_defences.py" crawl --todo "${TODO:?set TODO=<todo.json>}" --max-minutes 50
