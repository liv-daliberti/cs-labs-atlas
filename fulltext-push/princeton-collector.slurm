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
#SBATCH --output=/n/fs/resemble/cs-atlas/work/fulltext-push/logs/princeton-collector-%j.out
. /n/fs/resemble/cs-atlas/work/paths.sh  # every path in one place (tools/atlas_paths.py)
cd "$CS_ATLAS_FULLTEXT_PUSH"
./run_steps.sh princeton oar oa_arxiv openalex proceedings arxiv_title s2 core europepmc pmc figshare wayback_acm >> logs/steps-princeton.log 2>&1 < /dev/null &
nice -n 5 /usr/local/anaconda3/2024.02/bin/python -I -u lab_first_loop.py princeton --recent-first 2023 >> logs/lab_first_loop-princeton.out 2>&1 < /dev/null &
wait
