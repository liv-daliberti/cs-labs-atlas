#!/bin/bash
# usage: lpc.sh ID SCRIPT.py args   -- run a tools script with private capture DBs (scratchpad lpdb/<ID>-<school>.sqlite)
W="$1"; shift; SC="$1"; shift
export LPCAP_LOCAL_EPFL=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/lpdb/${W}-epfl.sqlite
export LPCAP_LOCAL_BERKELEY=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/lpdb/${W}-berkeley.sqlite
cd /tmp && exec /usr/local/anaconda3/2024.02/bin/python -I /n/fs/resemble/cs-atlas/work/hierarchy/labpage-tools-epfl-berkeley/$SC "$@"
