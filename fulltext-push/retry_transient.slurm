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
#SBATCH --output=/n/fs/resemble/cs-atlas/work/fulltext-push/logs/retry_transient-%j.out
cd /n/fs/resemble/cs-atlas/work/fulltext-push
for s in princeton cmu epfl mit berkeley stanford; do
  nice -n 5 /usr/local/anaconda3/2024.02/bin/python -I -u retry_transient.py $s &
  sleep 60
done
wait
