#!/bin/sh
# Round 2 of DSpace supervisor searches, started after round 1 exits (one DSpace client at a time).
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
cd "$(dirname "$0")"
while pgrep -f "python -I dspace_search.py$" >/dev/null 2>&1; do sleep 10; done
exec ${CS_ATLAS_PY} -I dspace_search.py \
  "dc.contributor.advisor:(Agarwal OR Moses OR Meyer OR Ward OR Long OR Mithal OR Lampson OR Seneff OR Liskov)" \
  "dc.contributor.advisor:(Terman OR Sipser OR Berners OR Goemans OR Sussman OR Cheng-Zhi OR (Huang AND Anna))"
