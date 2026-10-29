#!/bin/bash
#SBATCH --job-name=cs-related-candidates
#SBATCH --partition=all
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --time=00:55:00
#SBATCH --output=/n/fs/resemble/cs-atlas/work/hierarchy/logs/cs-related-candidates-%j.out
cd /n/fs/resemble/cs-atlas/work
/usr/bin/time -v /usr/local/anaconda3/2024.02/bin/python -u tools/cs_related_candidates.py "$@"
