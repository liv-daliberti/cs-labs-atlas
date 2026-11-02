#!/bin/bash
# Local reuse + DBLP for the regenerated lab-paper lists (2026-10-29): fresh missing/stores snapshot, a new DBLP scan
# for the current missing set, rematch from the inventory (no file re-read), then the identity-checked import.
#SBATCH --job-name=localreuse-round2
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=10G
#SBATCH --time=20:00:00
#SBATCH --output=fulltext-push/local-reuse/logs/round2-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1  # code of one commit, data shared (docs/CONTRIBUTING.md); submit with `atlas submit`
cd ${CS_ATLAS_FULLTEXT_PUSH}/local-reuse
export TMPDIR=${TMPDIR:-/tmp}
PY="nice -n 10 ${CS_ATLAS_COLLECTOR_PY} -I -u"
$PY lr_common.py snapshot && (cd .. && $PY dblp_ee.py scan) && $PY reuse_import.py rematch && $PY reuse_import.py import
