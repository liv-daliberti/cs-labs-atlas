#!/bin/sh
# Page-1 checks only (work lists already fetched), with a chosen number of parallel downloads: run_page1_pdf.sh <school> <workers>
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
cd "$(dirname "$0")/.."
TMPDIR=/tmp; export TMPDIR
nice -n 10 ${CS_ATLAS_PY} -u tools/pi_fulltext_affiliation.py pdf "$1" --workers "$2" >> hierarchy/page1-$1.log 2>&1
