#!/bin/sh
# Resumable driver: re-run plan_fetch for one school until every slot/year/half has a plan row
# (transient Wayback failures leave rows unplanned). Usage: run_school.sh <school> [max_rounds]
S=$1; N=${2:-12}
cd "$(dirname "$0")/.." || exit 1
PY="/usr/local/anaconda3/2024.02/bin/python -I -u"
i=0
while [ $i -lt $N ]; do
  i=$((i+1))
  echo "### round $i $(date -Is)"
  nice -n 5 $PY scripts/plan_fetch.py "$S"
  if $PY scripts/plan_fetch.py "$S" --check; then echo "### complete $(date -Is)"; exit 0; fi
  sleep 300
done
echo "### gave up after $N rounds $(date -Is)"
