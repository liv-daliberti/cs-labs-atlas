#!/bin/bash
# Submit (or top up) the e32 chain: sections for shards not complete, gpu for shards not complete, gpu task i after sections task i (aftercorr).
# Re-run any time: it only submits shards that are neither complete nor queued. usage: e32_submit.sh [ID]
set -euo pipefail
ID=${1:-20261123}
W=/n/fs/resemble/homogenizing-science/studies/homogenization/work/entropy32-$ID
cd "$(dirname "$0")"
N=$(python3 -c "import json;print(json.load(open('$W/RUN.json'))['nshards'])")
queued=$(squeue -r -u "$USER" -h -o "%j %K" | awk '$1~/^e32-/' )
need_sec=(); need_gpu=()
for i in $(seq 0 $((N-1))); do
  f=$W/sections/sections-$i.sqlite
  sdone=0; [ -f "$f" ] && [ "$(sqlite3 -readonly "$f" "select value from meta where key='complete'" 2>/dev/null)" = 1 ] && sdone=1
  [ $sdone = 0 ] && ! grep -qE "^e32-sections ($i)$" <<<"$queued" && need_sec+=($i)
  [ -f "$W/gpu/complete-$i" ] || { grep -qE "^e32-gpu ($i)$" <<<"$queued" || need_gpu+=($i); }
done
join() { local IFS=,; echo "$*"; }
dep=""
if [ ${#need_sec[@]} -gt 0 ]; then
  c=$(sbatch --parsable --array=$(join "${need_sec[@]}") --export=ALL,E32_ID=$ID e32_cpu.slurm); echo "sections: ${#need_sec[@]} shards -> $c"
fi
if [ ${#need_gpu[@]} -gt 0 ]; then
  # a gpu shard whose sections are still to run waits for them; the rest start now (shards share task ids, so aftercorr pairs them)
  wait_ids=(); now_ids=()
  for i in "${need_gpu[@]}"; do if printf '%s\n' "${need_sec[@]:-}" | grep -qx "$i"; then wait_ids+=($i); else now_ids+=($i); fi; done
  [ ${#wait_ids[@]} -gt 0 ] && { g=$(sbatch --parsable --array=$(join "${wait_ids[@]}")%${E32_GPU_MAX:-12} --dependency=aftercorr:$c --kill-on-invalid-dep=yes --export=ALL,E32_ID=$ID e32_gpu.slurm); echo "gpu after sections: ${#wait_ids[@]} -> $g"; }
  [ ${#now_ids[@]} -gt 0 ] && { g=$(sbatch --parsable --array=$(join "${now_ids[@]}")%${E32_GPU_MAX:-12} --export=ALL,E32_ID=$ID e32_gpu.slurm); echo "gpu now: ${#now_ids[@]} -> $g"; }
fi
echo "sections pending: ${#need_sec[@]}; gpu pending: ${#need_gpu[@]}"
