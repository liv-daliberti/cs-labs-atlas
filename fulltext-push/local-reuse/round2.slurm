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
#SBATCH --output=/n/fs/resemble/cs-atlas/work/fulltext-push/local-reuse/logs/round2-%j.out
cd /n/fs/resemble/cs-atlas/work/fulltext-push/local-reuse
export TMPDIR=${TMPDIR:-/tmp}
PY="nice -n 10 /usr/local/anaconda3/2024.02/bin/python -I -u"
$PY lr_common.py snapshot && (cd .. && $PY dblp_ee.py scan) && $PY reuse_import.py rematch && $PY reuse_import.py import
