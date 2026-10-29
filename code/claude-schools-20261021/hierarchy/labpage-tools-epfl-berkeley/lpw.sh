#!/bin/bash
# usage: lpw.sh WORKER_ID <lp.py args>   -- runs lp.py with this worker's private capture DBs
W="$1"; shift
export LPCAP_LOCAL_EPFL=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/lpdb/w${W}-epfl.sqlite
export LPCAP_LOCAL_BERKELEY=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/lpdb/w${W}-berkeley.sqlite
cd /tmp && exec /usr/local/anaconda3/2024.02/bin/python -I /n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/labpage-tools-epfl-berkeley/lp.py "$@"
