#!/bin/sh
# Re-run the Michigan sweep after each OpenAlex daily credit reset (00:00 UTC) until every year 2016-2026 is stored.
# Stops itself when the log shows the 2026 year line. pid in hierarchy/michigan/tmp/sweep_daily.pid
cd "$(dirname "$0")/../.." || exit 1
echo $$ > hierarchy/michigan/tmp/sweep_daily.pid
while :; do
  now=$(date -u +%s); next=$(( (now / 86400 + 1) * 86400 + 600 ))
  sleep $(( next - now ))
  hierarchy/michigan/run_sweep.sh
  if grep -q '"year": 2026, "works"' hierarchy/sweep-michigan.log; then echo "### complete $(date -Is)" >> hierarchy/sweep-michigan.log; exit 0; fi
done
