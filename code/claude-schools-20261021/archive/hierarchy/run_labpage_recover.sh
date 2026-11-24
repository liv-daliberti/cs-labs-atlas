#!/bin/bash
# Lab-page publication recovery (tools/labpage_recover.py), one school after another; OPENALEX_API_KEY from the scratchpad env file.
set -a; . $HOME/.config/cs-atlas/openalex.env; set +a
export TMPDIR=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
cd "$CS_ATLAS_WORK"
for s in "$@"; do
  nice ${CS_ATLAS_PY} -I -u tools/labpage_recover.py run $s --workers 6 --title-credits 600 >> hierarchy/labpage-recover-$s.log 2>&1
done
