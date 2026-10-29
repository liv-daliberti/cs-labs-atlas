#!/bin/bash
#SBATCH --job-name=dblp-index-candidates
#SBATCH --partition=all
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --time=00:55:00
#SBATCH --output=/n/fs/resemble/cs-atlas/work/hierarchy/logs/dblp-index-%j.out
. /n/fs/resemble/cs-atlas/work/paths.sh  # every path in one place (tools/atlas_paths.py)
cd "$CS_ATLAS_WORK"
PY=/usr/local/anaconda3/2024.02/bin/python
(cd "$CS_ATLAS_DBLP_DUMP" && md5sum -c dblp-2026-09-01.xml.gz.md5) || exit 1
/usr/bin/time -v $PY -u tools/dblp_dump_index.py && /usr/bin/time -v $PY -u tools/cs_related_candidates.py
