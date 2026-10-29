#!/bin/bash
# Wayback history for plan people pages, one shard per process, into worker-local stores (merged later with merge.py).
# The interactive store me-<school>.sqlite is read (not written) so the plan's manual rows resolve.
school=$1; shard=$2
cd /tmp
LPCAP_EXTRA=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/lp-local/me-$school.sqlite LPCAP_LOCAL=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/lp-local/wb-$school-${shard%/*}.sqlite exec /usr/local/anaconda3/2024.02/bin/python -I /n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/labpage-tools-princeton-mit/wbbatch.py $school --shard $shard
