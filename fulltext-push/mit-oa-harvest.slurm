#!/bin/bash
#SBATCH --job-name=mit-oa-harvest
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=1-12:00:00
#SBATCH --exclude=node302
#SBATCH --output=fulltext-push/logs/mit-oa-harvest-%j.out
# 2026-10-30: resume the DSpace@MIT Open Access Articles OAI-PMH harvest (37 of ~571 pages since 2026-10-27, stopped by
# 429 / Retry-After 900) at one request per 20 s, Retry-After honoured; robots.txt leaves /server/oai open and names no
# rule for this client. Then match the MIT lab papers to the items and resolve the new handles (lab_channels.py mit dspace,
# OAI-PMH ORE at 8 s per request) so the running mit loop downloads the manuscripts.
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
# compute nodes have no /usr/local/anaconda3: the project env (requests, no protego/bs4; nothing here needs them)
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export FTP_PY="$CS_ATLAS_ENV_PY"
cd "$CS_ATLAS_FULLTEXT_PUSH"
PY="$FTP_PY -I -u"
nice -n 5 $PY mit_oa_articles.py harvest >> logs/mit_oa_articles-harvest.log 2>&1
nice -n 5 $PY mit_oa_articles.py match >> logs/mit_oa_articles-harvest.log 2>&1
./run_steps.sh mit dspace >> logs/steps-mit.log 2>&1 < /dev/null
echo '{"mit-oa-harvest": "done"}'
