#!/bin/bash
# usage: w_b06_retry.sh <lp.py subcommand and args...>   retries on Wayback connection errors (max 4 tries)
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
export LABPAGE_DB=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/labpage-cmu/w-b06.sqlite
export LABPAGE_RO=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/labpage-cmu/crawl.sqlite
T=${CS_ATLAS_HIERARCHY}/labpage-tools-cmu
cd /tmp
for i in 1 2 3 4 5; do
  out=$(${CS_ATLAS_PY} -I $T/lp.py "$@" 2>&1)
  if echo "$out" | grep -q 'ConnectionError\|^0 captures'; then
    if [ "$1" = "cdx" ] && echo "$out" | grep -q '^0 captures'; then
      last=$(${CS_ATLAS_PY} -I -c "
import sqlite3,sys
c=sqlite3.connect('$LABPAGE_DB')
r=c.execute('select error from captures where url like \"%/cdx/search/cdx%\" order by id desc limit 1').fetchone()
print('ERR' if r and r[0] else 'OK')")
      if [ "$last" = "OK" ]; then echo "$out"; exit 0; fi
    fi
    echo "[retry $i]" >&2
    continue
  fi
  echo "$out"; exit 0
done
echo "$out"
