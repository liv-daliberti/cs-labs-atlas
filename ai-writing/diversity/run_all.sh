#!/bin/bash
# The diversity battery end to end (DESIGN-v2.md sections 2-3), one command. Rerun whenever papers.jsonl.gz,
# fulltext.sqlite, scores.jsonl.gz or paragraph_scores.jsonl.gz change; the AI variable switches to the paragraph
# detector by itself (AIW_AI_SOURCE=auto) unless AIW_AI_SOURCE=abstract is set.
#
# Login node (light):  snapshot fulltext.sqlite -> data/ft_snapshot.sqlite (short chunked reads, safe while fulltext.py
#                      writes); merge finished GPU chunks; export texts not yet embedded; submit_embed.sh (GPU, a5000,
#                      <= 2 in the queue); unit tests
# Compute node:        run_battery.slurm (32 CPUs, 24G; measured peak 9.2 GB): merge, paper features, lab diversity, analyses, figures,
#                      REPORT.md. Queued after any embedding jobs (afterany), so it uses their vectors. Non-blocking:
#                      results land in logs/battery-<job>.out, REPORT.md, figures/.
# Usage: run_all.sh [--local] [--no-submit]
#   --local      run the heavy steps here instead of in Slurm, with JOBS workers (default 8, under nice)
#   --no-submit  do not submit GPU embedding jobs
# Env: AIW_AI_SOURCE, AIW_DRAWS / AIW_BOOT / AIW_PERM (default 1000), JOBS
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"
ROOT=/n/fs/resemble/maxent-grpo
PY=/n/fs/resemble/cs-atlas-env/py310/bin/python
export LD_LIBRARY_PATH="$(dirname "$(readlink -f "$PY")")/../lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=/n/fs/resemble/cs-atlas-env/hf-cache HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
LOCAL_RUN=0; SUBMIT=1
for a in "$@"; do case "$a" in --local) LOCAL_RUN=1 ;; --no-submit) SUBMIT=0 ;; *) echo "unknown option $a"; exit 2 ;; esac; done
cd "$D"; mkdir -p logs data results figures
LOG="$D/logs/run_all-$(date +%Y%m%d-%H%M%S).log"
step() {
  echo "== $*" | tee -a "$LOG"
  nice -n 10 "$PY" -u "$@" 2>&1 | { grep -v -E "tensorflow|cudart|NVML|UserWarning|warnings.warn|real_accelerator|dso_loader" || true; } | tee -a "$LOG"
}
step embed_fulltext.py snapshot
step embed_fulltext.py merge
step embed_fulltext.py export
if [ "$SUBMIT" = 1 ]; then ./submit_embed.sh 2>&1 | tee -a "$LOG"; fi
step embed_fulltext.py status
step test_measures.py
if [ "$LOCAL_RUN" = 1 ]; then
  J=${JOBS:-8}
  export AIW_DIV_LOCAL=${AIW_DIV_LOCAL:-/tmp/aiw-diversity-$USER}
  OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 step paper_features.py -j "$J"
  step lab_diversity.py -j "$J"
  step analyze.py -j "$J"
  OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 step figures.py
  step report.py
  rm -rf "$AIW_DIV_LOCAL"
  echo "done: $D/REPORT.md (log $LOG)" | tee -a "$LOG"
  exit 0
fi
if [ "$(squeue -u "$USER" -h -n aiw-divbat -o %i | wc -l)" -ge 1 ]; then
  echo '{"battery": "already queued; not submitting another"}' | tee -a "$LOG"; exit 0
fi
deps=$(squeue -u "$USER" -h -n aiw-divemb -o %i | paste -sd: -)
dep=${deps:+--dependency=afterany:$deps}
jb=$(sbatch --parsable $dep run_battery.slurm)
echo "{\"battery_job\": \"$jb\", \"after_embedding_jobs\": \"${deps:-none}\", \"log\": \"$D/logs/battery-$jb.out\"}" | tee -a "$LOG"
