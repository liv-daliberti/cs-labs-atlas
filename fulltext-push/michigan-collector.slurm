#!/bin/bash
# Michigan full-text collection (protocol stage 8, 2026-10-30), modelled on stanford-collector.slurm: the open-copy
# channel steps (run_steps.sh, per-channel locks shared with the other schools) and the lab-first download loop run side
# by side; both resume from what the Michigan catalog already records (add_works.py seeds it first, on the login host).
# Compute nodes have no /usr/local/anaconda3, so the channels, the loop and its collector child (protego, bs4) run
# on the project env, which sits on shared storage (CS_ATLAS_COLLECTOR_PY / FTP_PY). Network-bound: a few cores suffice.
#SBATCH --job-name=michigan-fulltext
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=3-00:00:00
#SBATCH --output=fulltext-push/logs/michigan-collector-%j.out
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1  # submit from the code root  # every path in one place (tools/atlas_paths.py)
export CS_ATLAS_COLLECTOR_PY="$CS_ATLAS_PY"
export FTP_PY="$CS_ATLAS_COLLECTOR_PY"
cd "$CS_ATLAS_FULLTEXT_PUSH"
./run_steps.sh michigan oa_arxiv openalex proceedings arxiv_title dblp_ee s2 core europepmc pmc figshare labpages pihomes wayback_acm \
    >> logs/steps-michigan.log 2>&1 < /dev/null &
nice -n 5 $CS_ATLAS_COLLECTOR_PY -I -u lab_first_loop.py michigan --recent-first 2023 \
    >> logs/lab_first_loop-michigan.out 2>&1 < /dev/null &
wait
