#!/bin/bash
# Stanford PI works by anchored/reviewed OpenAlex id (tools/pi_fulltext_affiliation.py works), needed by the 2026-10-29
# unaffiliated-byline rule; Stanford had no pi-works.sqlite. API key sourced from ~/.config/cs-atlas (never printed).
#SBATCH --job-name=piworks-stanford
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=03:00:00
#SBATCH --output=/n/fs/resemble/cs-atlas/work/hierarchy/logs/piworks-stanford-%j.out
set -u
cd /n/fs/resemble/cs-atlas/work
set -a; . ~/.config/cs-atlas/openalex.env; set +a
export LD_LIBRARY_PATH=/n/fs/resemble/cs-atlas-env/py310/lib
/n/fs/resemble/cs-atlas-env/py310/bin/python -u tools/pi_fulltext_affiliation.py works stanford
