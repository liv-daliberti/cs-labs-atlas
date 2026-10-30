#!/bin/sh
# Resumable OpenAlex sweep for Stanford in month windows (tools/oa_sweep.py sweep_paged), now with the OpenAlex key from
# ~/.config/cs-atlas/openalex.env (copied there from soak on 2026-10-27; mode 600, never logged). Resumes from
# hierarchy/stanford/openalex-sweep.sqlite (table windows marks finished months); stops when 2026 is done.
# Check: tail hierarchy/sweep-stanford.log ("### complete"); pid in hierarchy/logs/stanford-sweep.pid
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
cd "$(dirname "$0")/.."
echo $$ > hierarchy/logs/stanford-sweep.pid
set -a; . "$HOME/.config/cs-atlas/openalex.env"; set +a
OPENALEX_FLOOR=1500 nice -n 10 ${CS_ATLAS_PY} -u tools/oa_sweep.py stanford >> hierarchy/sweep-stanford.log 2>&1
if grep -q '"year": 2026, "works"' hierarchy/sweep-stanford.log; then echo "### complete $(date -Is)" >> hierarchy/sweep-stanford.log; fi
