#!/bin/sh
# Page-1 affiliation checks for every school, one school at a time (work lists, then arXiv v1 page 1); resumable.
cd "$(dirname "$0")/.."
SP=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad
set -a; . $SP/openalex.env; OPENALEX_FLOOR=1500; TMPDIR=/tmp; set +a
for s in cmu mit princeton berkeley epfl; do
  echo "{\"school\": \"$s\", \"start\": \"$(date -u +%FT%TZ)\"}" >> hierarchy/page1-$s.log
  nice -n 10 /usr/local/anaconda3/2024.02/bin/python -u tools/pi_fulltext_affiliation.py works $s >> hierarchy/page1-$s.log 2>&1
  nice -n 10 /usr/local/anaconda3/2024.02/bin/python -u tools/pi_fulltext_affiliation.py pdf $s --workers 3 >> hierarchy/page1-$s.log 2>&1
done
echo "{\"page1_all\": \"done\", \"at\": \"$(date -u +%FT%TZ)\"}"
