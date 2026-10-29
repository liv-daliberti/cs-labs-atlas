#!/bin/bash
#SBATCH --job-name=cs-atlas-tree
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=06:00:00
#SBATCH --output=/n/fs/resemble/cs-atlas/work/hierarchy/logs/organize-tree-%j.out
# Rebuild the organized school -> lab -> papers tree under /n/fs/resemble/cs-atlas/schools (tools/organize_tree.py):
# refresh copies.json first so newly downloaded copies are linked.
. /n/fs/resemble/cs-atlas/work/paths.sh  # every path in one place (tools/atlas_paths.py)
cd "$CS_ATLAS_WORK"
export LD_LIBRARY_PATH=$CS_ATLAS_ENV_LIB
PY=$CS_ATLAS_ENV_PY
S=${SCHOOLS:-princeton cmu epfl mit berkeley stanford}
nice -n10 $PY -u tools/lab_paper_copies.py $S
nice -n10 ionice -c3 $PY -u tools/organize_tree.py $S
