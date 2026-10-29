#!/bin/sh
# Resumable OpenAlex sweep for Stanford in month windows (tools/oa_sweep.py sweep_paged), now with the OpenAlex key from
# ~/.config/cs-atlas/openalex.env (copied there from soak on 2026-10-27; mode 600, never logged). Resumes from
# hierarchy/stanford/openalex-sweep.sqlite (table windows marks finished months); stops when 2026 is done.
# Check: tail hierarchy/sweep-stanford.log ("### complete"); pid in hierarchy/logs/stanford-sweep.pid
cd "$(dirname "$0")/.."
echo $$ > hierarchy/logs/stanford-sweep.pid
set -a; . "$HOME/.config/cs-atlas/openalex.env"; set +a
OPENALEX_FLOOR=1500 nice -n 10 /usr/local/anaconda3/2024.02/bin/python -u tools/oa_sweep.py stanford >> hierarchy/sweep-stanford.log 2>&1
if grep -q '"year": 2026, "works"' hierarchy/sweep-stanford.log; then echo "### complete $(date -Is)" >> hierarchy/sweep-stanford.log; fi
