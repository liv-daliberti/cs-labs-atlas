#!/bin/sh
# Resumable keyless OpenAlex sweep for Stanford (2026-10-27). No OpenAlex API key is readable on wash, and cursor paging
# needs one, so tools/oa_sweep.py runs in keyless month-window mode on the shared free budget (1000 list queries/day per
# IP, reset 00:00 UTC). Each round resumes from hierarchy/stanford/openalex-sweep.sqlite (table windows marks finished
# months), spends down to OPENALEX_FLOOR, then sleeps until 00:10 UTC. Stops when every month 2016-2026 is done.
# Check: tail hierarchy/sweep-stanford.log; sqlite3 hierarchy/stanford/openalex-sweep.sqlite 'select count(*) from windows'
#        (132 month windows when complete; split months add rows); pid in hierarchy/logs/stanford-sweep.pid
cd "$(dirname "$0")/.."
echo $$ > hierarchy/logs/stanford-sweep.pid
i=0
while [ $i -lt 4 ]; do
  i=$((i+1))
  OPENALEX_FLOOR=60 nice -n 10 /usr/local/anaconda3/2024.02/bin/python -u tools/oa_sweep.py stanford >> hierarchy/sweep-stanford.log 2>&1
  if grep -q '"year": 2026, "works"' hierarchy/sweep-stanford.log; then echo "### complete $(date -Is)" >> hierarchy/sweep-stanford.log; exit 0; fi
  now=$(date -u +%s); next=$(( (now / 86400 + 1) * 86400 + 600 ))
  echo "### round $i stopped $(date -Is); sleeping until $(date -u -d @$next -Is)" >> hierarchy/sweep-stanford.log
  sleep $(( next - now ))
done
