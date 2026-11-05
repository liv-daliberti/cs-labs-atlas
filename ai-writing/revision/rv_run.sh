#!/bin/bash
# Re-run AI-in-revision (Experiment B): ONE command per stage. DETECTOR=v2 (default) or v3 (when ai-writing/detector_v3 has models/all/model + results/all/metrics.json).
#   rv_run.sh match      universe -> arXiv ids, bucket version listing   (CPU, ~10 min; no arxiv.org)
#   rv_run.sh fetch      plan + download/extract v1 and final PDFs (Slurm array, waits) + merge
#   rv_run.sh score      GPU scoring of the versions and the stored copies with $DETECTOR (Slurm array, waits; v2 stored copies are imported from the dose scores)
#   rv_run.sh analysis | report | all
# Environment: RV_UNIVERSE_DB (paper set), RV_DATA, RV_REPORT_DIR, DETECTOR, SCORE_GRES (default gpu:1), NSHARDS (8), RV_V3_MODEL / RV_V3_METRICS.
set -euo pipefail
HERE=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)
. "$HERE/../../paths.sh"
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
PY="$CS_ATLAS_ENV_PY -u"
DETECTOR="${DETECTOR:-v2}"; NSHARDS="${NSHARDS:-8}"
cd "$HERE"
waitfor() { $PY "$CS_ATLAS_TOOLS/slurm_wait.py" "$@" || true; }
match() { $PY rv_match.py match; $PY rv_match.py versions -j 6; }
fetch() {
  $PY rv_fetch.py plan --max-a "${MAX_A:-4000}" --max-s "${MAX_S:-5000}"
  jid=$(sbatch --parsable --array=0-31%16 rv_fetch.slurm 32); waitfor "$jid"
  $PY rv_fetch.py merge
}
score() {
  ids=""
  jid=$(sbatch --parsable --array=0-$((NSHARDS - 1))%4 --export=ALL,DETECTOR=$DETECTOR ${SCORE_GRES:+--gres=$SCORE_GRES} rv_score.slurm "$NSHARDS"); ids=$jid
  if [ "$DETECTOR" = v2 ]; then $PY rv_score.py --detector v2 --source stored --import-v2 --tag "r$(date +%Y%m%d)"
  else
    jid2=$(sbatch --parsable --array=0-$((NSHARDS - 1))%4 --export=ALL,DETECTOR=$DETECTOR,SOURCE=stored ${SCORE_GRES:+--gres=$SCORE_GRES} rv_score.slurm "$NSHARDS"); ids="$ids $jid2"
  fi
  waitfor $ids
}
analysis() { $PY rv_analysis.py --detector "$DETECTOR" --boot "${RV_BOOT:-500}"; }
report() { $PY rv_report.py --detector "$DETECTOR"; }
case "${1:-all}" in
  all) match; fetch; score; analysis; report;;
  match) match;; fetch) fetch;; score) score;; analysis) analysis;; report) report;;
  *) echo "usage: rv_run.sh match|fetch|score|analysis|report|all" >&2; exit 2;;
esac
