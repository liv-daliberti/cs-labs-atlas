#!/bin/bash
# The heavy half of the diversity battery on a compute node: merge finished GPU chunks, paper features (k-means,
# text measures), lab diversity (1,000 equal-size draws per lab-period), analyses (bootstraps, permutations), figures,
# REPORT.md. The full-text snapshot (data/ft_snapshot.sqlite) is copied to node-local /tmp first, and every
# intermediate stays there. Submitted by run_all.sh, after any embedding jobs it submitted (afterany).
#SBATCH --job-name=aiw-divbat
#SBATCH --partition=all
#SBATCH --account=allcs
#SBATCH --cpus-per-task=32
#SBATCH --mem=24G
#SBATCH --time=00:59:00
#SBATCH --output=/n/fs/resemble/cs-atlas/work/ai-writing/diversity/logs/battery-%j.out
set -euo pipefail
ROOT=/n/fs/resemble/maxent-grpo
D=/n/fs/resemble/cs-atlas/work/ai-writing/diversity
PY=/n/fs/resemble/cs-atlas-env/py310/bin/python
export LD_LIBRARY_PATH="$(dirname "$(readlink -f "$PY")")/../lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=/n/fs/resemble/cs-atlas-env/hf-cache HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export AIW_DIV_LOCAL=/tmp/aiw-divbat-$SLURM_JOB_ID
export AIW_SNAPSHOT=$AIW_DIV_LOCAL/ft_snapshot.sqlite
JOBS=${SLURM_CPUS_PER_TASK:-32}
mkdir -p "$AIW_DIV_LOCAL"
trap 'rm -rf "$AIW_DIV_LOCAL"' EXIT
cd "$D"
step() { echo "== $* ($(date +%T))"; "$PY" -u "$@" 2>&1 | { grep -v -E "tensorflow|cudart|NVML|UserWarning|warnings.warn|real_accelerator|dso_loader" || true; }; }
# merge finished GPU chunks into the store BEFORE copying it: copied first, the local store missed them (fixed 2026-10-28)
step embed_fulltext.py merge
cp "$D/data/ft_snapshot.sqlite" "$AIW_SNAPSHOT"
# the 3 GB full-text embedding store too: read page by page over the share it stalled paper_features (2026-10-28)
export AIW_EMB_STORE=$AIW_DIV_LOCAL/fulltext_emb.sqlite
cp "$D/data/fulltext_emb.sqlite" "$AIW_EMB_STORE"
echo "{\"node\": \"$(hostname)\", \"ai_source\": \"${AIW_AI_SOURCE:-auto}\", \"draws\": \"${AIW_DRAWS:-1000}\"}"
step embed_fulltext.py status
step test_measures.py
OMP_NUM_THREADS=16 OPENBLAS_NUM_THREADS=16 step paper_features.py -j "$JOBS"
step lab_diversity.py -j "$JOBS"
step analyze.py -j "$JOBS"
OMP_NUM_THREADS=16 OPENBLAS_NUM_THREADS=16 step figures.py
step report.py
echo "== done ($(date +%T))"
