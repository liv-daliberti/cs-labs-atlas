#!/bin/bash
# Citation fetchers for papers new to paragraph_scores.jsonl.gz (2026-10-28: Stanford added): OpenAlex citing works,
# then the cited works not yet cached; Semantic Scholar reference lists in parallel. Each skips what
# /n/fs/resemble/cs-atlas-cache/citations already holds, and fetch.py pauses at its OpenAlex budget reserve.
#SBATCH --job-name=cit-fetch-new
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=1-00:00:00
#SBATCH --output=ai-writing/citations/logs/fetch-new-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd ${CS_ATLAS_AI_WRITING}/citations
PY=${CS_ATLAS_ENV_PY}
echo "{\"node\": \"$(hostname)\", \"start\": \"$(date -u +%FT%TZ)\"}"
nice -n 10 $PY -u s2fetch.py run >> logs/s2fetch-new-20261028.log 2>&1 &
nice -n 10 $PY -u fetch.py citing >> logs/fetch_citing-new-20261028.log 2>&1
nice -n 10 $PY -u fetch.py works >> logs/fetch_works-new-20261028.log 2>&1
nice -n 10 $PY -u fetch.py missing >> logs/fetch_works-new-20261028.log 2>&1  # singletons (free) for ids the list query did not return
wait
nice -n 10 $PY -u fetch.py status
nice -n 10 $PY -u s2fetch.py status
echo "{\"end\": \"$(date -u +%FT%TZ)\"}"
