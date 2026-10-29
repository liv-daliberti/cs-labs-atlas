#!/bin/bash
# The figures -> lab classifier over every embedded figure: by-year accuracy 2016-2026 (all eligible labs, and the same
# labs every year over 2018-2025) and the AI-flagged vs unflagged gap.
#SBATCH --job-name=figlab-classify
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --output=/n/fs/resemble/cs-atlas/work/ai-writing/figlab/logs/classify-%j.out
cd /n/fs/resemble/cs-atlas/work/ai-writing/figlab
PY=/n/fs/resemble/cs-atlas-env/py310/bin/python
export OMP_NUM_THREADS=1  # parallel over draws/folds instead (classify.py --jobs)
$PY -u classify.py --L 20 --K 8 --draws 100 --folds 4 --K-ai 6 --min-figs 1 --years 2016-2026 --tag _L20
$PY -u classify.py --L 10 --K 8 --draws 100 --folds 4 --K-ai 6 --min-figs 1 --years 2018-2025 --tag _L10_2018_2025
