#!/bin/sh
# Page-1 affiliation checks for every school, one school at a time (work lists, then arXiv v1 page 1); resumable.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
cd "$(dirname "$0")/.."
SP=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad
set -a; . $HOME/.config/cs-atlas/openalex.env; OPENALEX_FLOOR=1500; TMPDIR=/tmp; set +a
for s in cmu mit princeton berkeley epfl; do
  echo "{\"school\": \"$s\", \"start\": \"$(date -u +%FT%TZ)\"}" >> hierarchy/page1-$s.log
  nice -n 10 ${CS_ATLAS_PY} -u tools/pi_fulltext_affiliation.py works $s >> hierarchy/page1-$s.log 2>&1
  nice -n 10 ${CS_ATLAS_PY} -u tools/pi_fulltext_affiliation.py pdf $s --workers 3 >> hierarchy/page1-$s.log 2>&1
done
echo "{\"page1_all\": \"done\", \"at\": \"$(date -u +%FT%TZ)\"}"
