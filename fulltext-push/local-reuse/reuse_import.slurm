#!/bin/bash
# Local-reuse passes 3-4: inventory + proposals (reuse_import.py plan), then the identity-checked import (reuse_import.py
# import), which waits for each catalog's free .collector.lock before writing.
#SBATCH --job-name=localreuse-import
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=20:00:00
#SBATCH --output=/n/fs/resemble/cs-atlas/work/fulltext-push/local-reuse/logs/import-%j.out
cd /n/fs/resemble/cs-atlas/work/fulltext-push/local-reuse
export TMPDIR=${TMPDIR:-/tmp}
PY="nice -n 10 /usr/local/anaconda3/2024.02/bin/python -I -u"
$PY reuse_import.py plan && $PY reuse_import.py import
