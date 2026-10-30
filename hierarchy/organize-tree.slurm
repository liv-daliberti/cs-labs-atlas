#!/bin/bash
#SBATCH --job-name=cs-atlas-tree
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=06:00:00
#SBATCH --output=hierarchy/logs/organize-tree-%j.out
# Rebuild the organized school -> lab -> papers tree under /n/fs/resemble/cs-atlas/schools (tools/organize_tree.py) from
# the latest release (releases/latest; RELEASE=<id> picks another), refreshing copies.json first and linking those fresh
# copies (--fresh-copies), so PDFs downloaded since the release are linked while the labs and papers stay the release's.
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd "$CS_ATLAS_WORK"
PY=$CS_ATLAS_PY  # the project interpreter (tools/atlas_paths.py)
S=${SCHOOLS:-princeton cmu epfl mit berkeley stanford}
nice -n10 $PY -u tools/lab_paper_copies.py $S
nice -n10 ionice -c3 $PY -u tools/organize_tree.py --release "${RELEASE:-latest}" --fresh-copies $S
