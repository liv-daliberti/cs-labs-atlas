#!/bin/bash
# submit_chain.sh TAG VARIANT HOLDOUT [LINKS=4]: train links (afterany, each resumes from the checkpoint) then score (afterok on the last link)
set -euo pipefail
S=ai-writing/detector_v4/detector4.slurm; TAG=$1; VAR=$2; HOLD=$3; N=${4:-4}
H=(); [ "$HOLD" != none ] && H=(--holdout "$HOLD")
B=(); [ -n "${BASE:-}" ] && B=(--base "$BASE")
prev=""
for i in $(seq 1 $N); do
  dep=(); [ -n "$prev" ] && dep=(--dependency=afterany:$prev)
  prev=$(sbatch --parsable ${SB:-} "${dep[@]}" $S train --tag "$TAG" --variant "$VAR" "${H[@]}" "${B[@]}")
done
sc=$(sbatch --parsable ${SB:-} --dependency=afterok:$prev $S score --tag "$TAG" --variant "$VAR")
echo "$TAG: train chain ending $prev, score $sc"
