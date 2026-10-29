#!/bin/bash
# Lab-page publication recovery (tools/labpage_recover.py), one school after another; OPENALEX_API_KEY from the scratchpad env file.
set -a; . $HOME/.config/cs-atlas/openalex.env; set +a
export TMPDIR=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad
. /n/fs/resemble/cs-atlas/work/paths.sh  # every path in one place (tools/atlas_paths.py)
cd "$CS_ATLAS_WORK"
for s in "$@"; do
  nice /usr/local/anaconda3/2024.02/bin/python -I -u tools/labpage_recover.py run $s --workers 6 --title-credits 600 >> hierarchy/labpage-recover-$s.log 2>&1
done
