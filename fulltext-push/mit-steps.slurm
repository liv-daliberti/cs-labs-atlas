#!/bin/bash
#SBATCH --job-name=mit-steps
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=6G
#SBATCH --time=2-00:00:00
#SBATCH --exclude=node302
#SBATCH --output=/n/fs/resemble/cs-atlas/work/fulltext-push/logs/mit-steps-%j.out
# mit open-copy channels for the 7,324 lab papers added 2026-10-28 (add_works.py), under the per-channel locks; the mit
# download loop keeps running in mit-fulltext (32011930), whose own step runner waited on the old global lock and was stopped
. /n/fs/resemble/cs-atlas/work/paths.sh  # every path in one place (tools/atlas_paths.py)
cd "$CS_ATLAS_FULLTEXT_PUSH"
./run_steps.sh mit oa_arxiv openalex proceedings arxiv_title s2 core europepmc pmc figshare dspace labpages pihomes wayback_acm >> logs/steps-mit.log 2>&1 < /dev/null
