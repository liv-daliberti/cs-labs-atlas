#!/bin/bash
# Requeue transient download failures of missing lab papers (retry_transient.py), every school side by side; each
# waits for its catalog's free .collector.lock (between collector passes) before deleting the attempt rows.
#SBATCH --job-name=fulltext-retry-transient
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=16:00:00
#SBATCH --output=fulltext-push/logs/retry_transient-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1  # code of one commit, data shared (docs/CONTRIBUTING.md); submit with `atlas submit`
cd "$CS_ATLAS_FULLTEXT_PUSH"
for s in princeton cmu epfl mit berkeley stanford; do
  nice -n 5 ${CS_ATLAS_COLLECTOR_PY} -I -u retry_transient.py $s &
  sleep 60
done
wait
