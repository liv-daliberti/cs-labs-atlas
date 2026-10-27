#!/bin/bash
#SBATCH --job-name=cs-related-candidates
#SBATCH --partition=all
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --time=00:55:00
#SBATCH --output=/n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/logs/cs-related-candidates-%j.out
cd /n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021
/usr/bin/time -v /usr/local/anaconda3/2024.02/bin/python -u tools/cs_related_candidates.py "$@"
