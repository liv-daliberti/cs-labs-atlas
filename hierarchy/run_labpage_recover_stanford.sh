#!/bin/sh
# Lab-page publication recovery for Stanford (tools/labpage_recover.py), 2026-10-27. Key from ~/.config/cs-atlas/openalex.env
# (never logged). Run after run_dblp_recover_stanford.sh finishes: both fetch proceedings hosts and their per-host
# delays do not coordinate across processes.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
cd "$(dirname "$0")/.."
set -a; . "$HOME/.config/cs-atlas/openalex.env"; set +a
export TMPDIR=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad
echo "### start $(date -Is)" >> hierarchy/labpage-recover-stanford.log
nice -n 10 ${CS_ATLAS_PY} -I -u tools/labpage_recover.py run stanford --workers 6 --title-credits 600 >> hierarchy/labpage-recover-stanford.log 2>&1
echo "### done $(date -Is) rc=$?" >> hierarchy/labpage-recover-stanford.log
