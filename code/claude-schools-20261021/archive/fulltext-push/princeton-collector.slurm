#!/bin/bash
# princeton full-text push (2026-10-28): the open-copy channels that never ran for this school (per-channel locks since
# 2026-10-28, so schools run different channels side by side), with the lab-first download loop alongside.
#SBATCH --job-name=princeton-fulltext
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=3-00:00:00
#SBATCH --output=fulltext-push/logs/princeton-collector-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd "$CS_ATLAS_FULLTEXT_PUSH"
./run_steps.sh princeton oar oa_arxiv openalex proceedings arxiv_title s2 core europepmc pmc figshare wayback_acm >> "$CS_ATLAS_FT_LOGS"/steps-princeton.log 2>&1 < /dev/null &
nice -n 5 ${CS_ATLAS_COLLECTOR_PY} -I -u lab_first_loop.py princeton --recent-first 2023 >> "$CS_ATLAS_FT_LOGS"/lab_first_loop-princeton.out 2>&1 < /dev/null &
wait
