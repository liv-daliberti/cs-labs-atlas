#!/bin/bash
# Full run: one array task = one entropy-32 shard (0-63). Survives session loss: a task that stops for its budget (exit 75) or is handed an
# occupied card (exit 3) resubmits ITSELF for the same shard (same partition/account/time/model/KV), up to SUM_MAXGEN generations.
# Halt everything: touch $W/STOP (no task resubmits; running ones finish their chunk). Launch / top up: sum_submit.sh.
#SBATCH --job-name=sum14b
#SBATCH --gres=gpu:a6000:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --exclude=node206
#SBATCH --output=/n/fs/resemble/homogenizing-science/studies/homogenization/work/summaries14b-20261123/logs/full-%A_%a.out
set -uo pipefail
. /n/fs/resemble/homogenizing-science/code/paths.sh || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false VLLM_USE_V1=0
export TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID} TMPDIR=/tmp/sum14b-${SLURM_JOB_ID}; mkdir -p $TMPDIR; trap 'rm -rf $TMPDIR $TRITON_CACHE_DIR' EXIT
HERE=/n/fs/resemble/homogenizing-science/worktrees/summaries-14b/ai-writing/summaries
W=/n/fs/resemble/homogenizing-science/studies/homogenization/work/summaries14b-${SUM_ID:-20261123}
SHARD=${SUM_SHARD:-$SLURM_ARRAY_TASK_ID}; GEN=${SUM_GEN:-0}
cd $HERE
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader
used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
if [ "${used:-0}" -lt 2000 ]; then
  $CS_ATLAS_ENV_PY -u summarize.py run --shard "$SHARD" --budget "${SUM_BUDGET:-3000}"; rc=$?
else
  echo "{\"refused_gpu\": \"$(hostname)\", \"used_mib\": $used}"; rc=3
fi
echo "{\"shard\": $SHARD, \"gen\": $GEN, \"rc\": $rc}"
if { [ $rc = 75 ] || [ $rc = 3 ]; } && [ ! -e $W/STOP ] && [ $GEN -lt ${SUM_MAXGEN:-40} ]; then
  ex=node206; [ $rc = 3 ] && ex="$ex,$(hostname -s)"
  j=$(sbatch --parsable --partition=$SLURM_JOB_PARTITION --account=$SLURM_JOB_ACCOUNT --time=${SUM_TIME:-00:59:00} --exclude=$ex \
      --job-name=sum14b-$SHARD --export=ALL,SUM_SHARD=$SHARD,SUM_GEN=$((GEN+1)) $HERE/sum_full.slurm)
  echo "{\"resubmitted\": \"$j\", \"shard\": $SHARD, \"gen\": $((GEN+1))}"
  echo "$(date -u +%FT%TZ) shard=$SHARD gen=$((GEN+1)) job=$j after rc=$rc" >> $W/resubmits.log
fi
exit $rc
