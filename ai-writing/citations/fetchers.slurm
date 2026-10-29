#!/bin/bash
# Citation-analysis fetchers, resumed from resemble after the cutover (2026-10-28): OpenAlex cited-work metadata and
# Semantic Scholar reference lists. Both skip what /n/fs/resemble/cs-atlas-cache/citations already holds.
#SBATCH --job-name=cit-fetchers
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=3-00:00:00
#SBATCH --output=/n/fs/resemble/cs-atlas/work/ai-writing/citations/logs/fetchers-%j.out
cd /n/fs/resemble/cs-atlas/work/ai-writing/citations
PY=/n/fs/resemble/cs-atlas-env/py310/bin/python
nice -n 10 $PY -u fetch.py works >> logs/fetch_works.log 2>&1 &
nice -n 10 $PY -u s2fetch.py run >> logs/s2fetch.log 2>&1 &
wait
