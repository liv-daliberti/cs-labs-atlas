#!/bin/bash
#SBATCH --job-name=cc-fill
#SBATCH --partition=all
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=06:00:00
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --output=%x-%j.out
# Common Crawl fill for ONE school on a PRIVATE copy of its captures.sqlite (docs/COMMONCRAWL.md).
# sbatch listings/scripts/cc_fill.slurm <school> <private-db> [--slot X ...] [--gap-crawls]
# Resumable: the cdx cache in the db and the state file make a re-run ask nothing twice. Exit 4 = Common Crawl robots refuse (nothing fetched).
set -u
school=$1; db=$2; shift 2
. "$(cd "${SLURM_SUBMIT_DIR:-.}" && git rev-parse --show-toplevel)/paths.sh" || exit 1
cd "$CS_ATLAS_CODE/listings/scripts" 2>/dev/null || cd "$(dirname "$0")"
exec ${CS_ATLAS_PY} -I -u cc_fill.py "$school" --db "$db" --state "$db.cc-state.json" "$@"
