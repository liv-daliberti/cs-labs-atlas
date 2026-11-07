#!/bin/bash
# Re-run the citation-novelty study (Experiment A) from the paper list: ONE command per stage, all configured by paths (cn_common.py env overrides).
#   cn_run.sh all            prepare + stream (Slurm, waits) + merge + measures + analysis + report
#   cn_run.sh stream | measures | analysis | report
# Environment: CN_UNIVERSE_DB / CN_OA_EXTRA (the paper set: after a rebuild of the universe re-run dose/oa_extra.py first), CN_DATA, CN_REPORT_DIR, CN_SAMPLE_MOD, CN_OF (tasks, 128).
# Stream cost: 128 CPU tasks x ~6 min (2 CPUs, 8 GB), no OpenAlex API credits (S3 snapshot).
set -euo pipefail
HERE=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)
. "$HERE/../../paths.sh"
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
PY="$CS_ATLAS_ENV_PY -u"
OF="${CN_OF:-128}"
cd "$HERE"
stage="${1:-all}"
stream() {
  $PY cn_stream.py prepare
  jid=$(sbatch --parsable --array=0-$((OF - 1))%32 --export=ALL,CN_OF=$OF cn_stream.slurm)
  $PY "$CS_ATLAS_TOOLS/slurm_wait.py" "$jid" || true
  $PY cn_stream.py merge --of "$OF"
}
measures() { $PY cn_measures.py paper; $PY cn_measures.py lab; }
analysis() { $PY cn_analysis.py all --boot "${CN_BOOT:-200}"; }
report() { $PY cn_report.py; }
case "$stage" in
  all) stream; measures; analysis; report;;
  stream) stream;; measures) measures;; analysis) analysis;; report) report;;
  *) echo "usage: cn_run.sh all|stream|measures|analysis|report" >&2; exit 2;;
esac
