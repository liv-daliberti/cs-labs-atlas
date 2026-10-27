#!/bin/sh
# Page-1 checks only (work lists already fetched), with a chosen number of parallel downloads: run_page1_pdf.sh <school> <workers>
cd "$(dirname "$0")/.."
TMPDIR=/tmp; export TMPDIR
nice -n 10 /usr/local/anaconda3/2024.02/bin/python -u tools/pi_fulltext_affiliation.py pdf "$1" --workers "$2" >> hierarchy/page1-$1.log 2>&1
