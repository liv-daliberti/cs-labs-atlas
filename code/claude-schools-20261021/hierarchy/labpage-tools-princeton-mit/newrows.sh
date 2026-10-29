#!/bin/bash
# usage: newrows.sh SCHOOL "PI" ["PI" ...] -- dry-run those PIs and print their NEW rows compactly
school=$1; shift
S=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/lp-local
source $S/env-$school.sh
cd /tmp
/usr/local/anaconda3/2024.02/bin/python -I /n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/labpage-tools-princeton-mit/build.py $school --module dec_${school}_main --dry -v --pi "$@" 2>&1 | grep -v " PUB " | awk '/^== /{print; next} /NEW/{$1=""; printf "  %s\n", $0} /^[A-Z].* held /{print}' | cut -c1-150
