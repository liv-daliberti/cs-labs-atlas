#!/bin/bash
#SBATCH --job-name=unavailable-ledger
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=2
#SBATCH --mem=20G
#SBATCH --time=1-00:00:00
#SBATCH --exclude=node302
#SBATCH --output=fulltext-push/logs/ledger-%j.out
# The unavailability ledger (docs/UNAVAILABLE.md) for the six released schools: the coverage counter first (copies.json),
# then every applicable source's check (cached / reused when fresh), then hierarchy/<school>/unavailable.jsonl.gz.
# SCHOOLS overrides the school list; LEDGER_ARGS passes options (e.g. --offline).
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
# compute nodes have no /usr/local/anaconda3: the project env (requests, no protego/bs4; nothing here needs them)
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export FTP_PY="$CS_ATLAS_PY"  # the pinned project env (2026-10-31)
cd "$CS_ATLAS_WORK"
S=${SCHOOLS:-princeton cmu epfl mit berkeley stanford}
nice -n 5 $FTP_PY -I -u tools/lab_paper_copies.py $S
/usr/bin/time -v nice -n 5 $FTP_PY -I -u fulltext-push/unavailable_ledger.py $S ${LEDGER_ARGS:-}
