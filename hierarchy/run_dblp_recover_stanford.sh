#!/bin/sh
# DBLP-listed lab-paper recovery for Stanford (tools/dblp_recover.py), 2026-10-27. Key from ~/.config/cs-atlas/openalex.env
# (keyed singleton DOI lookups; never logged). usage: run_dblp_recover_stanford.sh <years A-B>
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
cd "$(dirname "$0")/.."
set -a; . "$HOME/.config/cs-atlas/openalex.env"; set +a
export TMPDIR=/tmp DBLP_RECOVER_YEARS="${1:-2016-2026}"
echo "### start $(date -Is) years=$DBLP_RECOVER_YEARS" >> hierarchy/dblp-recover-stanford.log
nice -n 10 ${CS_ATLAS_PY} -I -u tools/dblp_recover.py stanford --workers 6 >> hierarchy/dblp-recover-stanford.log 2>&1
echo "### done $(date -Is) rc=$?" >> hierarchy/dblp-recover-stanford.log
