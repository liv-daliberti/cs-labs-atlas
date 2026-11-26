#!/bin/bash
# Full run in LANES: lane L (0..N-1) owns shards L, L+N, L+2N, ... of the 64 entropy-32 shards and works through them in order. Each job runs
# under the 59-minute `all` lane; when it stops for budget (exit 75) or is handed an occupied card (exit 3) it resubmits ITSELF for the same
# lane, so at most N jobs exist at any time and nothing depends on an interactive session. Halt: touch $W/STOP. Launch: sum_submit.sh.
#SBATCH --job-name=sum14b-lane
#SBATCH --gres=gpu:a6000:2
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --exclude=node206
#SBATCH --output=/n/fs/resemble/homogenizing-science/studies/homogenization/work/summaries14b-20261123/logs/full-%j.out
set -uo pipefail
. /n/fs/resemble/homogenizing-science/code/paths.sh || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=8
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false VLLM_USE_V1=${SUM_V1:-1} SUM_TP=${SUM_TP:-2}
export TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID} TMPDIR=/tmp/sum14b-${SLURM_JOB_ID}; mkdir -p $TMPDIR; trap 'rm -rf $TMPDIR $TRITON_CACHE_DIR' EXIT
HERE=/n/fs/resemble/homogenizing-science/worktrees/summaries-14b/ai-writing/summaries
W=/n/fs/resemble/homogenizing-science/studies/homogenization/work/summaries14b-${SUM_ID:-20261123}
LANE=${SUM_LANE:?}; LANES=${SUM_LANES:?}; GEN=${SUM_GEN:-0}; T0=$(date +%s); BUDGET=${SUM_BUDGET:-3100}
cd $HERE
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader
complete() { [ -f "$1" ] && [ "$(sqlite3 -readonly "$1" "select value from meta where key='complete'" 2>/dev/null)" = 1 ]; }
used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | sort -n | tail -1)
rc=0
if [ "${used:-0}" -ge 2000 ]; then
  echo "{\"refused_gpu\": \"$(hostname)\", \"used_mib\": $used}"; rc=3
else
  for ((s = LANE; s < 64; s += LANES)); do
    complete $W/shards/sum-$s.sqlite && continue
    left=$((BUDGET - ($(date +%s) - T0)))
    [ $left -gt 1300 ] || { rc=75; break; }      # not enough time left for a model load (~3 min) and one 96-paper chunk (~17 min)
    SUM_CHUNK=${SUM_CHUNK:-96} $CS_ATLAS_ENV_PY -u summarize.py run --shard $s --budget $left; rc=$?
    [ $rc = 0 ] || break
  done
fi
echo "{\"lane\": $LANE, \"gen\": $GEN, \"rc\": $rc}"
if { [ $rc = 75 ] || [ $rc = 3 ]; } && [ ! -e $W/STOP ] && [ $GEN -lt ${SUM_MAXGEN:-150} ]; then
  ex=node206; [ $rc = 3 ] && ex="$ex,$(hostname -s)"
  j=$(sbatch --parsable --partition=$SLURM_JOB_PARTITION --account=$SLURM_JOB_ACCOUNT --time=${SUM_TIME:-00:59:00} --exclude=$ex \
      --job-name=sum14b-lane$LANE --export=ALL,SUM_LANE=$LANE,SUM_GEN=$((GEN+1)) $HERE/sum_full.slurm)
  echo "{\"resubmitted\": \"$j\", \"lane\": $LANE, \"gen\": $((GEN+1))}"
  echo "$(date -u +%FT%TZ) lane=$LANE gen=$((GEN+1)) job=$j after rc=$rc" >> $W/resubmits.log
elif [ $rc != 0 ]; then
  echo "$(date -u +%FT%TZ) lane=$LANE gen=$GEN STOPPED rc=$rc (see logs/full-$SLURM_JOB_ID.out)" >> $W/resubmits.log
else
  echo "$(date -u +%FT%TZ) lane=$LANE gen=$GEN DONE" >> $W/resubmits.log
fi
exit $rc
