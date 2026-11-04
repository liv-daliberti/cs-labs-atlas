#!/bin/bash
#SBATCH --job-name=defense-scan
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=2-00:00:00
#SBATCH --exclude=node302
#SBATCH --output=/n/fs/resemble/homogenizing-science/code/hierarchy/uchicago/tmp/etdwork/defense-scan-%j.out
# 2026-11-04 Wayback retry of the event, news, CAM tag and old directory routes for UChicago's labs at 0 students (tools/defense_scan.py).
# No polling by us: every request waits for host_throttle's shared web.archive.org slot and its 429 cooldown (listings/scripts/wb.py), so the job simply sits out a cooldown.
# Output (hand read afterwards): hierarchy/uchicago/tmp/etdwork/defense-scan.json; the captures are stored in the school's captures db.
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
export FTP_PY="$CS_ATLAS_PY"
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
export PYTHONPATH="$CS_ATLAS_TOOLS:$CS_ATLAS_CODE/listings/scripts:$CS_ATLAS_CODE/fulltext-push"
cd "$CS_ATLAS_TOOLS"
OUT="$CS_ATLAS_CODE/hierarchy/uchicago/tmp/etdwork/defense-scan.json"
"$CS_ATLAS_PY" -u defense_scan.py uchicago '[["cs.uchicago.edu/events/","event"],["stat.uchicago.edu/events/","event"],["cam.uchicago.edu/events/","event"],["cam.uchicago.edu/tags/","event"],["www.ttic.edu/events/","event"],["ttic.edu/events/","event"],["cs.uchicago.edu/news/","news"],["stat.uchicago.edu/news/","news"],["cam.uchicago.edu/news/","news"],["www.cs.uchicago.edu/directories/","dir"],["www.math.uchicago.edu/people/","dir"]]' 150 "$OUT" < /dev/null
echo '{"defense-scan": "done"}'
