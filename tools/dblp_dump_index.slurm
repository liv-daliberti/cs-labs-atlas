#!/bin/bash
#SBATCH --job-name=dblp-index-candidates
#SBATCH --partition=all
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --time=00:55:00
#SBATCH --output=hierarchy/logs/dblp-index-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1  # code of one commit, data in the main checkout (docs/CONTRIBUTING.md); submit with `atlas submit`
cd "$CS_ATLAS_WORK"
PY=${CS_ATLAS_PY}
(cd "$CS_ATLAS_DBLP_DUMP" && md5sum -c dblp-2026-09-01.xml.gz.md5) || exit 1
/usr/bin/time -v $PY -u "$CS_ATLAS_TOOLS"/dblp_dump_index.py && /usr/bin/time -v $PY -u "$CS_ATLAS_TOOLS"/cs_related_candidates.py
