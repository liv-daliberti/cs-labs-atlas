#!/bin/bash
# submit.sh <script.py> [args]   (sbatch options in SBATCH_EXTRA): test-only first, refuse on "Preempts:", then submit from this checkout's committed HEAD.
set -euo pipefail
WT=$(cd "$(dirname "$0")/../.." && pwd)
CODE=${CS_ATLAS_CODE:-/n/fs/resemble/homogenizing-science/code}
export SNAPSHOT_REPO=$WT CS_ATLAS_SNAPSHOT_COMMIT=$(git -C "$WT" rev-parse HEAD)
cd "$CODE"
S="$WT/ai-writing/labstudy/labstudy.slurm"
T=$(sbatch --test-only ${SBATCH_EXTRA:-} "$S" "$@" 2>&1) || { echo "$T"; exit 1; }
echo "$T"
case "$T" in *Preempts:*) echo "refusing: test-only shows Preempts"; exit 1;; esac
sbatch --parsable --export=ALL,SNAPSHOT_REPO,CS_ATLAS_SNAPSHOT_COMMIT ${SBATCH_EXTRA:-} "$S" "$@"
