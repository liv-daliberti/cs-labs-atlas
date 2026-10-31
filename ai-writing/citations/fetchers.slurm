#!/bin/bash
# Citation-analysis fetchers, resumed from resemble after the cutover (2026-10-28): OpenAlex cited-work metadata and
# Semantic Scholar reference lists. Both skip what /n/fs/resemble/homogenizing-science/cache/citations already holds.
#SBATCH --job-name=cit-fetchers
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=3-00:00:00
#SBATCH --output=ai-writing/citations/logs/fetchers-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd ${CS_ATLAS_AI_WRITING}/citations
PY=${CS_ATLAS_ENV_PY}
nice -n 10 $PY -u fetch.py works >> logs/fetch_works.log 2>&1 &
nice -n 10 $PY -u s2fetch.py run >> logs/s2fetch.log 2>&1 &
wait
