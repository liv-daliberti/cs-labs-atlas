#!/bin/bash
#SBATCH --job-name=s2-rerun
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=6G
#SBATCH --time=1-00:00:00
#SBATCH --exclude=node302
#SBATCH --output=fulltext-push/logs/s2-rerun-%j.out
# the Semantic Scholar channel failed on every compute node on 2026-10-28 (its pacing file sat in a login-host /tmp
# scratchpad); rerun it where it failed, plus Stanford's figshare step, which its collector never listed
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd "$CS_ATLAS_FULLTEXT_PUSH"
./run_steps.sh princeton s2 >> "$CS_ATLAS_FT_LOGS"/steps-princeton.log 2>&1 < /dev/null
./run_steps.sh epfl s2 >> "$CS_ATLAS_FT_LOGS"/steps-epfl.log 2>&1 < /dev/null
./run_steps.sh berkeley s2 >> "$CS_ATLAS_FT_LOGS"/steps-berkeley.log 2>&1 < /dev/null
./run_steps.sh stanford s2 figshare >> "$CS_ATLAS_FT_LOGS"/steps-stanford.log 2>&1 < /dev/null
