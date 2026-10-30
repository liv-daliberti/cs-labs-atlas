#!/bin/bash
# Stanford full-text collection, resumed from resemble after the similarity -> resemble cutover (2026-10-28).
# The channel steps (run_steps.sh) and the lab-first download loop run side by side, as before the pause; both resume
# from what catalog.sqlite already records. Network-bound, so a few cores are plenty.
#SBATCH --job-name=stanford-fulltext
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=3-00:00:00
#SBATCH --output=fulltext-push/logs/stanford-collector-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd "$CS_ATLAS_FULLTEXT_PUSH"
./run_steps.sh stanford openalex proceedings arxiv_title s2 core europepmc pmc labpages pihomes wayback_acm \
    >> logs/steps-stanford.log 2>&1 < /dev/null &
nice -n 5 ${CS_ATLAS_COLLECTOR_PY} -I -u lab_first_loop.py stanford --recent-first 2023 \
    >> logs/lab_first_loop-stanford.out 2>&1 < /dev/null &
wait
