#!/bin/bash
#SBATCH --job-name=unavailable-ledger
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=2
#SBATCH --mem=20G
#SBATCH --time=1-00:00:00
#SBATCH --exclude=node302
#SBATCH --output=/n/fs/resemble/cs-atlas/work/fulltext-push/logs/ledger-%j.out
# The unavailability ledger (docs/UNAVAILABLE.md) for the six released schools: the coverage counter first (copies.json),
# then every applicable source's check (cached / reused when fresh), then hierarchy/<school>/unavailable.jsonl.gz.
# SCHOOLS overrides the school list; LEDGER_ARGS passes options (e.g. --offline).
. /n/fs/resemble/cs-atlas/work/paths.sh
# compute nodes have no /usr/local/anaconda3: the project env (requests, no protego/bs4; nothing here needs them)
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export FTP_PY="$CS_ATLAS_ENV_PY"
cd "$CS_ATLAS_WORK"
S=${SCHOOLS:-princeton cmu epfl mit berkeley stanford}
nice -n 5 $FTP_PY -I -u tools/lab_paper_copies.py $S
/usr/bin/time -v nice -n 5 $FTP_PY -I -u fulltext-push/unavailable_ledger.py $S ${LEDGER_ARGS:-}
