#!/bin/sh
set -a; . /tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/openalex.env; set +a
cd /n/fs/resemble/cs-atlas/work/hierarchy/gap-tools-cmu
for a in "$@"; do echo "######## $a"; /usr/local/anaconda3/2024.02/bin/python -I oa.py works $a --n 40; done
