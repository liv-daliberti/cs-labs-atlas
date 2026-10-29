#!/bin/bash
# Discovery crawl for one school into a worker-local capture DB (merged later by merge.py).
school=$1
cd /tmp
LPCAP_LOCAL=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/lp-local/disc-$school.sqlite exec /usr/local/anaconda3/2024.02/bin/python -I /n/fs/resemble/cs-atlas/work/hierarchy/labpage-tools-princeton-mit/disc.py $school --threads 10
