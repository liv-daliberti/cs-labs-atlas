#!/bin/bash
# MIT full-text collection for the 7,324 lab papers add_works.py put in the catalog on 2026-10-28.
# The channel steps (run_steps.sh) and the lab-first download loop run side by side, as before the pause; both resume
# from what catalog.sqlite already records. Network-bound, so a few cores are plenty.
#SBATCH --job-name=mit-fulltext
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=3-00:00:00
#SBATCH --output=/n/fs/resemble/cs-atlas/work/fulltext-push/logs/mit-collector-%j.out
cd /n/fs/resemble/cs-atlas/work/fulltext-push
./run_steps.sh mit oa_arxiv openalex proceedings arxiv_title s2 core europepmc pmc labpages pihomes wayback_acm \
    >> logs/steps-mit.log 2>&1 < /dev/null &
nice -n 5 /usr/local/anaconda3/2024.02/bin/python -I -u lab_first_loop.py mit --recent-first 2023 \
    >> logs/lab_first_loop-mit.out 2>&1 < /dev/null &
wait
