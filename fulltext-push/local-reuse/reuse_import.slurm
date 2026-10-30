#!/bin/bash
# Local-reuse passes 3-4: inventory + proposals (reuse_import.py plan), then the identity-checked import (reuse_import.py
# import), which waits for each catalog's free .collector.lock before writing.
#SBATCH --job-name=localreuse-import
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=20:00:00
#SBATCH --output=fulltext-push/local-reuse/logs/import-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd ${CS_ATLAS_FULLTEXT_PUSH}/local-reuse
export TMPDIR=${TMPDIR:-/tmp}
PY="nice -n 10 ${CS_ATLAS_COLLECTOR_PY} -I -u"
$PY reuse_import.py plan && $PY reuse_import.py import
