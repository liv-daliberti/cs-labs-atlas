#!/bin/bash
# OpenReview (owner's account, R-STU-27 as extended by D-0047): list accepted ICLR 2018-2023 (cached, resumes), then fetch their PDFs one chunk at a time
# (>= 10 s between requests, shared lock). A stop-for-the-day (429/401/403/challenge) exits 76; the job then re-queues itself for the next UTC day.
#SBATCH --job-name=e32-orfetch
#SBATCH --partition=all
#SBATCH --account=allcs
#SBATCH --cpus-per-task=1
#SBATCH --mem=6G
#SBATCH --time=00:59:00
#SBATCH --exclude=node302,node014
#SBATCH --output=/n/fs/resemble/homogenizing-science/studies/homogenization/work/entropy32-20261123/logs/orfetch-%j.out
set -uo pipefail
. /n/fs/resemble/homogenizing-science/code/paths.sh || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" PYTHONDONTWRITEBYTECODE=1
HERE=/n/fs/resemble/homogenizing-science/worktrees/ai-entropy-32/ai-writing/entropy32
W=/n/fs/resemble/homogenizing-science/studies/homogenization/work/entropy32-20261123-field
cd $HERE
tomorrow() { sbatch --begin="$(date -d "$(date -u -d 'tomorrow 00:05' '+%Y-%m-%d %H:%M:%S') UTC" '+%Y-%m-%dT%H:%M:%S')" "$HERE/e32_orfetch.slurm"; }
if ! grep -q 'openreview (D-0047)' $W/RUN.json; then
  $CS_ATLAS_ENV_PY -u fieldft.py extend_or; rc=$?
  if [ $rc -ne 0 ]; then echo "listing stopped (rc $rc); re-queue for the next UTC day"; tomorrow; exit 0; fi
fi
# the next OpenReview chunk that is not complete
read F L < <(python3 -c "import json;r=json.load(open('$W/RUN.json'));e=[x for x in r['extensions'] if 'openreview' in x.get('source','')][-1];print(*e['chunks'])")
for i in $(seq $F $L); do
  if [ "$(sqlite3 -readonly $W/sections/sections-$i.sqlite "select value from meta where key='complete'" 2>/dev/null)" != 1 ]; then
    $CS_ATLAS_ENV_PY -u fieldft.py fetch $i --budget 3000; rc=$?
    if [ $rc -eq 76 ]; then echo "stopped for the day on chunk $i"; tomorrow; exit 0; fi
    if [ $rc -eq 0 ]; then sbatch --export=ALL,E32_ID=20261123-field --array=$i e32_gpu.slurm; fi
    sbatch "$HERE/e32_orfetch.slurm"     # next chunk (or the rest of this one) in a fresh job; the 10 s lock keeps one request at a time
    exit 0
  fi
done
echo "all OpenReview chunks complete"
