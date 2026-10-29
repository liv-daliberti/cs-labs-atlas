#!/bin/bash
# cmu full-text push (2026-10-28): the open-copy channels that never ran for this school (per-channel locks since
# 2026-10-28, so schools run different channels side by side), with the lab-first download loop alongside.
#SBATCH --job-name=cmu-fulltext
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=3-00:00:00
#SBATCH --output=/n/fs/resemble/cs-atlas/work/fulltext-push/logs/cmu-collector-%j.out
cd /n/fs/resemble/cs-atlas/work/fulltext-push
./run_steps.sh cmu  oa_arxiv openalex proceedings arxiv_title s2 core europepmc pmc figshare wayback_acm >> logs/steps-cmu.log 2>&1 < /dev/null &
nice -n 5 /usr/local/anaconda3/2024.02/bin/python -I -u lab_first_loop.py cmu --recent-first 2023 >> logs/lab_first_loop-cmu.out 2>&1 < /dev/null &
wait
