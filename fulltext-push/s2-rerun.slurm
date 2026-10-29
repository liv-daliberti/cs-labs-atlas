#!/bin/bash
#SBATCH --job-name=s2-rerun
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=6G
#SBATCH --time=1-00:00:00
#SBATCH --exclude=node302
#SBATCH --output=/n/fs/resemble/cs-atlas/work/fulltext-push/logs/s2-rerun-%j.out
# the Semantic Scholar channel failed on every compute node on 2026-10-28 (its pacing file sat in a login-host /tmp
# scratchpad); rerun it where it failed, plus Stanford's figshare step, which its collector never listed
. /n/fs/resemble/cs-atlas/work/paths.sh  # every path in one place (tools/atlas_paths.py)
cd "$CS_ATLAS_FULLTEXT_PUSH"
./run_steps.sh princeton s2 >> logs/steps-princeton.log 2>&1 < /dev/null
./run_steps.sh epfl s2 >> logs/steps-epfl.log 2>&1 < /dev/null
./run_steps.sh berkeley s2 >> logs/steps-berkeley.log 2>&1 < /dev/null
./run_steps.sh stanford s2 figshare >> logs/steps-stanford.log 2>&1 < /dev/null
