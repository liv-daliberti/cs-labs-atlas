#!/bin/bash
#SBATCH --job-name=dblp-index-candidates
#SBATCH --partition=all
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --time=00:55:00
#SBATCH --output=/n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/logs/dblp-index-%j.out
cd /n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021
PY=/usr/local/anaconda3/2024.02/bin/python
(cd /n/fs/similarity/maxent-grpo/var/data/dblp-dump && md5sum -c dblp-2026-09-01.xml.gz.md5) || exit 1
/usr/bin/time -v $PY -u tools/dblp_dump_index.py && /usr/bin/time -v $PY -u tools/cs_related_candidates.py
