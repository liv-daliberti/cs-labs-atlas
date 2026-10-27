#!/bin/sh
# Resumable driver for profile-page fetches: re-run until every target half has a pplan row.
S=$1; N=${2:-12}
cd "$(dirname "$0")/.." || exit 1
PY="/usr/local/anaconda3/2024.02/bin/python -I -u"
i=0
while [ $i -lt $N ]; do
  i=$((i+1))
  echo "### round $i $(date -Is)"
  nice -n 5 $PY scripts/profiles.py "$S"
  if $PY scripts/profiles.py "$S" --check; then echo "### complete $(date -Is)"; exit 0; fi
  sleep 300
done
echo "### gave up after $N rounds $(date -Is)"
