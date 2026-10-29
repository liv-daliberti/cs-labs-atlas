#!/bin/sh
# Recover DBLP-listed lab papers (tools/dblp_recover.py), one school after another (OpenAlex and proceedings hosts see one client).
cd "$(dirname "$0")/.."
SP=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad
set -a; . $SP/openalex.env; TMPDIR=/tmp; set +a
for s in "$@"; do nice -n 10 /usr/local/anaconda3/2024.02/bin/python -u tools/dblp_recover.py $s --workers 6 >> hierarchy/dblp-recover-$s.log 2>&1; done
