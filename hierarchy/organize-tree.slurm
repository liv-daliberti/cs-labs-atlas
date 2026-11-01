#!/bin/bash
#SBATCH --job-name=cs-atlas-tree
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=06:00:00
#SBATCH --output=hierarchy/logs/organize-tree-%j.out
# Rebuild the organized school -> lab -> papers tree under /n/fs/resemble/homogenizing-science/schools ("$CS_ATLAS_TOOLS"/organize_tree.py) from
# the latest release (releases/latest; RELEASE=<id> picks another), refreshing copies.json first and linking those fresh
# copies (--fresh-copies), so PDFs downloaded since the release are linked while the labs and papers stay the release's.
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd "$CS_ATLAS_WORK"   # the data
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1   # the code: one commit, immune to landings (docs/CONTRIBUTING.md)
PY=$CS_ATLAS_PY  # the project interpreter (tools/atlas_paths.py)
S=${SCHOOLS:-$CS_ATLAS_SCHOOLS}  # the released charters (tools/atlas_paths.py SCHOOL_IDS)
nice -n10 $PY -u "$CS_ATLAS_TOOLS"/lab_paper_copies.py $S
nice -n10 ionice -c3 $PY -u "$CS_ATLAS_TOOLS"/organize_tree.py --release "${RELEASE:-latest}" --fresh-copies $S
