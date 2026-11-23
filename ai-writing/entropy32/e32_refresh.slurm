#!/bin/bash
# Daily refresh (owner 2026-11-23: pick up new full texts as the download loops fetch them).
# 1) e32.py delta: re-read the store catalogs; papers with a copy that no earlier round split form round N (WORK-dN)
# 2) sections array -> gpu array (aftercorr) -> e32.py paper + analyze.py all on the base (merges every round, re-runs every figure)
# 3) re-submits itself for tomorrow. Stop it: touch <WORK>/REFRESH_STOP (checked before any work) or scancel the pending e32-refresh job.
#SBATCH --job-name=e32-refresh
#SBATCH --partition=all
#SBATCH --account=allcs
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --exclude=node302,node014
#SBATCH --output=/n/fs/resemble/homogenizing-science/studies/homogenization/work/entropy32-20261123/logs/refresh-%j.out
set -uo pipefail
. /n/fs/resemble/homogenizing-science/code/paths.sh || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" PYTHONDONTWRITEBYTECODE=1
ID=${E32_BASE:-20261123}
W=/n/fs/resemble/homogenizing-science/studies/homogenization/work/entropy32-$ID
HERE=/n/fs/resemble/homogenizing-science/worktrees/ai-entropy-32/ai-writing/entropy32
cd "$HERE"
if [ -e "$W/REFRESH_STOP" ]; then echo "REFRESH_STOP present: not running, not rescheduling"; exit 0; fi
# never stack rounds: if an earlier round's jobs are still queued or running, only reschedule
if squeue -u "$USER" -h -o "%j" | grep -qE '^e32-(sections|gpu|analyze|schools|schools-prep|schools-figs|ftrefs|ftrefs-merge)$'; then
  echo "earlier round still in the queue; skipping today"
else
  out=$($CS_ATLAS_ENV_PY -u e32.py delta --id "$ID" --min-new 200 | tee /dev/stderr | grep -E '^DELTA=')
  D=$(sed -n 's/^DELTA=\([^ ]*\).*/\1/p' <<<"$out"); N=$(sed -n 's/.*NSHARDS=\([0-9]*\).*/\1/p' <<<"$out")
  if [ -n "$D" ] && [ "$D" != none ]; then
    c=$(sbatch --parsable --array=0-$((N-1)) --export=ALL,E32_ID=$D e32_cpu.slurm)
    g=$(sbatch --parsable --array=0-$((N-1))%14 --dependency=aftercorr:$c --kill-on-invalid-dep=yes --export=ALL,E32_ID=$D e32_gpu.slurm)
    # citation years from the new papers' reference sections (same shards), then re-merge the table
    t=$(sbatch --parsable --array=0-$((N-1)) --dependency=aftercorr:$c --kill-on-invalid-dep=yes --export=ALL,E32_BASE=$ID,FTREFS_DIR=entropy32-$D e32_ftrefs.slurm)
    tm=$(sbatch --parsable --dependency=afterok:$t --kill-on-invalid-dep=yes --job-name=e32-ftrefs-merge --cpus-per-task=2 --mem=16G --time=00:20:00 \
        --output=$W/logs/ftrefs-merge-%j.out --wrap="cd $HERE && $CS_ATLAS_ENV_PY -u ftrefs.py merge --id $ID && $CS_ATLAS_ENV_PY -u ftrefs.py check --id $ID")
    a=$(sbatch --parsable --dependency=afterok:$g:$tm --kill-on-invalid-dep=yes --export=ALL,E32_ID=$ID,STAGE=all e32_analyze.slurm)
    # per-school figures after the all-schools run (prep re-selects schools with >= 1,000 papers in 2023-25 and rewrites their views)
    p=$(sbatch --parsable --dependency=afterok:$a --kill-on-invalid-dep=yes --job-name=e32-schools-prep --cpus-per-task=4 --mem=32G --time=00:30:00 \
        --output=$W/logs/schools-prep-%j.out --wrap="cd $HERE && $CS_ATLAS_ENV_PY -u schools.py prep --id $ID")
    s=$(sbatch --parsable --dependency=afterok:$p --kill-on-invalid-dep=yes --array=0-39 e32_schools.slurm)
    f=$(sbatch --parsable --dependency=afterok:$p --kill-on-invalid-dep=yes --job-name=e32-schools-figs --cpus-per-task=8 --mem=32G --time=00:30:00 \
        --output=$W/logs/schools-figs-%j.out --wrap="cd $HERE && $CS_ATLAS_ENV_PY -u schools.py cosine_fig --id $ID && $CS_ATLAS_ENV_PY -u schools.py citeage_fig --id $ID")
    echo "round $D: $N shards; sections $c gpu $g analyze $a schools-prep $p schools $s"
  fi
fi
sbatch --begin=now+1day --export=ALL,E32_BASE=$ID "$HERE/e32_refresh.slurm" && echo "rescheduled for tomorrow"
