#!/bin/sh
# Michigan OpenAlex institution sweep (tools/oa_sweep.py; lineage I27837315 OR related I4210114445 from
# schools/michigan.toml), resumable. Key from ~/.config/cs-atlas/openalex.env (never printed). Protocol stage 2/7 input.
cd "$(dirname "$0")/../.." || exit 1
set -a; . ~/.config/cs-atlas/openalex.env; set +a
echo "### start $(date -Is)" >> hierarchy/sweep-michigan.log
OPENALEX_FLOOR=1500 nice -n 10 /usr/local/anaconda3/2024.02/bin/python -I -u tools/oa_sweep.py michigan >> hierarchy/sweep-michigan.log 2>&1
echo "### done $(date -Is) rc=$?" >> hierarchy/sweep-michigan.log
