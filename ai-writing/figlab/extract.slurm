#!/bin/bash
# Figure extraction for the figures -> lab classifier: one manifest shard per array task (CPU).
#SBATCH --job-name=figlab-extract
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=06:00:00
#SBATCH --array=0-31%16
#SBATCH --output=/n/fs/resemble/cs-atlas/work/ai-writing/figlab/logs/extract-%A_%a.out
cd /n/fs/resemble/cs-atlas/work/ai-writing/figlab
/n/fs/resemble/cs-atlas-env/py310/bin/python -u extract.py --shard $SLURM_ARRAY_TASK_ID --of 32
