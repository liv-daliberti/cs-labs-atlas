#!/bin/sh
# PI work lists and page-1 affiliation checks (tools/pi_fulltext_affiliation.py), one process per school; resumable.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
cd "$(dirname "$0")/.."
SP=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad
set -a; . $HOME/.config/cs-atlas/openalex.env; OPENALEX_FLOOR=1500; TMPDIR=/tmp; set +a
for s in "$@"; do (nice -n 10 ${CS_ATLAS_PY} -u tools/pi_fulltext_affiliation.py works $s && nice -n 10 ${CS_ATLAS_PY} -u tools/pi_fulltext_affiliation.py pdf $s --workers 3) > hierarchy/page1-$s.log 2>&1 & done
wait
